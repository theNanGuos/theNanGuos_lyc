from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator, Awaitable, Callable, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from the_nanguos.config import RuntimeConfigurationError, load_project_env
from the_nanguos.memory import PreferenceStore
from the_nanguos.schemas import ConductorResult, SongSpec, SunoModel, UserProfile
from the_nanguos.services.jobs import GenerationRecord, Runner, TaskRegistry
from the_nanguos.services.storage import safe_filename
from the_nanguos.services.runtime import environment_previewer, environment_runner


GenerationWeight = Annotated[float, Field(ge=0, le=1, multiple_of=0.01)]
Previewer = Callable[[str, dict[str, object]], Awaitable[ConductorResult]]
_monotonic = time.monotonic
PREVIEW_TTL_SECONDS = 30 * 60


class GenerationOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str | None = Field(default=None, min_length=2, max_length=16)
    instrumental: bool | None = None
    vocal_gender: Literal["m", "f"] | None = None
    suno_model: SunoModel | None = None
    title: str | None = Field(default=None, min_length=1, max_length=100)
    custom_mode: bool | None = None
    negative_tags: str | None = Field(default=None, max_length=1000)
    style_weight: GenerationWeight | None = None
    weirdness_constraint: GenerationWeight | None = None
    audio_weight: GenerationWeight | None = None


class CreateGeneration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=10_000)
    overrides: GenerationOverrides = Field(default_factory=GenerationOverrides)
    save_defaults: list[Literal["language", "instrumental", "vocal_gender", "suno_model"]] = Field(default_factory=list)
    preview_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    approved_song_spec: SongSpec | None = None
    retention_limit: int | None = Field(default=1, strict=True)

    @field_validator("retention_limit")
    @classmethod
    def validate_retention_limit(cls, value: int | None) -> int | None:
        if value not in (1, 2, None):
            raise ValueError("retention_limit must be 1, 2, or null")
        return value

    @model_validator(mode="after")
    def require_complete_preview_pair(self) -> "CreateGeneration":
        if (self.preview_id is None) != (self.approved_song_spec is None):
            raise ValueError("preview_id and approved_song_spec must be provided together")
        return self


class StylePayload(BaseModel):
    markdown: str = Field(max_length=100_000)


def _find_audio(outputs: Path, request_id: str, audio_id: str) -> tuple[Path, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", request_id) or not re.fullmatch(r"[A-Za-z0-9_-]+", audio_id):
        raise HTTPException(404, "audio not found")
    path = outputs / request_id / "audio" / f"{audio_id}.mp3"
    log_path = outputs / request_id / "collaboration_log.json"
    if not path.is_file() or not log_path.is_file(): raise HTTPException(404, "audio not found")
    try:
        log = json.loads(log_path.read_text(encoding="utf-8"))
        item = next(item for item in log["suno"]["audio_results"] if item["id"] == audio_id)
    except (OSError, ValueError, KeyError, StopIteration, TypeError) as exc:
        raise HTTPException(404, "audio not found") from exc
    return path, str(item.get("title") or audio_id)


def _parse_range(header: str, size: int) -> tuple[int, int]:
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match: raise HTTPException(416, "invalid range", headers={"Content-Range": f"bytes */{size}"})
    first, last = match.groups()
    if not first and not last: raise HTTPException(416, "invalid range")
    if first:
        start, end = int(first), int(last) if last else size - 1
    else:
        length = int(last); start, end = max(0, size - length), size - 1
    if start >= size or end < start: raise HTTPException(416, "range not satisfiable", headers={"Content-Range": f"bytes */{size}"})
    return start, min(end, size - 1)


def create_app(*, outputs_dir: Path | str = "outputs", memory_dir: Path | str = "memory", runner: Runner | None = None, previewer: Previewer | None = None) -> FastAPI:
    outputs = Path(outputs_dir)
    preferences = PreferenceStore(memory_dir)
    registry = TaskRegistry(outputs, runner)
    previews: dict[str, tuple[str, ConductorResult, float]] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        outputs.mkdir(parents=True, exist_ok=True)
        registry.reindex()
        app.state.registry = registry
        yield
        await registry.shutdown()

    application = FastAPI(title="theNanGuos", lifespan=lifespan)
    application.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

    @application.post("/api/generation-previews")
    async def create_generation_preview(payload: CreateGeneration):
        if previewer is None:
            raise HTTPException(503, "generation preview unavailable")
        override_data = payload.overrides.model_dump(mode="json", exclude_none=True)
        try:
            result = await previewer(payload.prompt, override_data)
        except RuntimeConfigurationError as exc:
            raise HTTPException(503, str(exc)) from exc
        song_spec = result.song_spec
        updates: dict[str, object] = {}
        if "title" in override_data:
            updates["title"] = override_data["title"]
        if "language" in override_data:
            updates["language"] = override_data["language"]
        if override_data.get("instrumental") is True:
            updates["vocal"] = song_spec.vocal.model_copy(update={"enabled": False, "gender": None})
        elif "vocal_gender" in override_data or override_data.get("instrumental") is False:
            gender = {"m": "male", "f": "female"}.get(str(override_data.get("vocal_gender"))) or song_spec.vocal.gender
            updates["vocal"] = song_spec.vocal.model_copy(update={"enabled": True, "gender": gender})
        if updates:
            result = result.model_copy(update={"song_spec": song_spec.model_copy(update=updates)})
        preview_id = uuid.uuid4().hex
        previews[preview_id] = (payload.prompt, result, _monotonic())
        return {
            "preview_id": preview_id,
            "song_spec": result.song_spec.model_dump(mode="json"),
            "task_plan": result.task_plan.model_dump(mode="json"),
        }

    @application.post("/api/generations", status_code=202)
    async def create_generation(payload: CreateGeneration):
        request_id = uuid.uuid4().hex
        override_data = payload.overrides.model_dump(mode="json", exclude_none=True)
        approved_result: ConductorResult | None = None
        if payload.preview_id is not None:
            saved_preview = previews.pop(payload.preview_id, None)
            if saved_preview is None or saved_preview[0] != payload.prompt or _monotonic() - saved_preview[2] > PREVIEW_TTL_SECONDS:
                raise HTTPException(409, "generation preview unavailable or already used")
            approved_result = saved_preview[1]
        if payload.save_defaults:
            existing = preferences.load_defaults().model_dump(exclude={"schema_version"})
            existing.update({key: override_data[key] for key in payload.save_defaults if key in override_data})
            preferences.save_defaults(existing)
        record = GenerationRecord(
            request_id=request_id,
            user_request=payload.prompt,
            options=override_data,
            retention_limit=payload.retention_limit,
            approved_song_spec=payload.approved_song_spec if approved_result else None,
            approved_task_plan=approved_result.task_plan if approved_result else None,
        )
        registry.start(record)
        return {"request_id": request_id, "status": record.status}

    @application.get("/api/generations")
    async def list_generations(search: str = "", status: str | None = None, sort: Literal["newest", "oldest"] = "newest"):
        items = list(registry.records.values())
        if search: items = [item for item in items if search.casefold() in item.user_request.casefold() or any(search.casefold() in str(c.get("title", "")).casefold() for c in item.candidates)]
        if status: items = [item for item in items if item.status == status]
        items.sort(key=lambda item: item.created_at, reverse=sort == "newest")
        return {"items": [item.public() for item in items]}

    @application.get("/api/generations/{request_id}")
    async def get_generation(request_id: str):
        record = registry.records.get(request_id)
        if record is None: raise HTTPException(404, "generation not found")
        return record.public()

    @application.delete("/api/generations/{request_id}", status_code=204)
    async def delete_generation(request_id: str):
        try:
            await registry.delete(request_id)
        except KeyError as exc:
            raise HTTPException(404, "generation not found") from exc
        except RuntimeError as exc:
            raise HTTPException(409, "生成任务仍在运行，请先停止等待") from exc
        except (OSError, ValueError) as exc:
            raise HTTPException(500, "作品文件删除失败，请关闭占用文件后重试") from exc
        return Response(status_code=204)

    @application.post("/api/generations/{request_id}/stop-waiting")
    async def stop_waiting(request_id: str):
        record = registry.records.get(request_id)
        if record is None: raise HTTPException(404, "generation not found")
        record.stop_event.set(); record.transition(status="stopped", stage="stopped_waiting", progress=record.progress)
        log_path = outputs / request_id / "collaboration_log.json"
        if log_path.exists():
            try:
                data = json.loads(log_path.read_text(encoding="utf-8")); data["suno"]["status"] = "STOPPED_WAITING"
                temporary = log_path.with_suffix(".json.tmp"); temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(temporary, log_path)
            except (OSError, ValueError, TypeError, KeyError): pass
        return {"request_id": request_id, "status": record.status, "message": "已停止本地轮询，远程生成可能继续"}

    @application.post("/api/generations/{request_id}/resume-polling", status_code=202)
    async def resume_polling(request_id: str):
        record = registry.records.get(request_id)
        if record is None or not record.task_id: raise HTTPException(409, "no remote task available to resume")
        if runner is None: raise HTTPException(503, "generation runner unavailable")
        record.stop_event = __import__("asyncio").Event(); record.transition(status="queued", stage="resume_polling", progress=record.progress)
        registry.start(record)
        return {"request_id": request_id, "status": record.status}

    @application.get("/api/generations/{request_id}/audio/{audio_id}")
    async def stream_audio(request_id: str, audio_id: str, range_header: str | None = Header(default=None, alias="Range")):
        path, _ = _find_audio(outputs, request_id, audio_id)
        size = path.stat().st_size
        if range_header is None: return FileResponse(path, media_type="audio/mpeg", headers={"Accept-Ranges": "bytes"})
        start, end = _parse_range(range_header, size)
        def chunks() -> AsyncIterator[bytes]:
            with path.open("rb") as source:
                source.seek(start); remaining = end - start + 1
                while remaining:
                    chunk = source.read(min(64 * 1024, remaining))
                    if not chunk: break
                    remaining -= len(chunk); yield chunk
        return StreamingResponse(chunks(), status_code=206, media_type="audio/mpeg", headers={"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{size}", "Content-Length": str(end-start+1)})

    @application.get("/api/generations/{request_id}/audio/{audio_id}/download")
    async def download_audio(request_id: str, audio_id: str):
        path, title = _find_audio(outputs, request_id, audio_id)
        return FileResponse(path, media_type="audio/mpeg", filename=f"{safe_filename(title, audio_id)}.mp3")

    @application.get("/api/generations/{request_id}/cover/{audio_id}")
    async def get_cover(request_id: str, audio_id: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", request_id) or not re.fullmatch(r"[A-Za-z0-9_-]+", audio_id): raise HTTPException(404, "cover not found")
        paths = list((outputs / request_id / "covers").glob(f"{audio_id}.*"))
        if len(paths) != 1: raise HTTPException(404, "cover not found")
        return FileResponse(paths[0])

    @application.get("/api/preferences")
    async def get_preferences(): return {"defaults": preferences.load_defaults().model_dump(mode="json"), "style_markdown": preferences.load_style()}

    @application.put("/api/preferences/defaults")
    async def put_defaults(payload: UserProfile): return preferences.save_defaults(payload.model_dump(exclude={"schema_version"})).model_dump(mode="json")

    @application.put("/api/preferences/style")
    async def put_style(payload: StylePayload): preferences.save_style(payload.markdown); return {"style_markdown": payload.markdown}

    @application.delete("/api/preferences", status_code=204)
    async def clear_preferences(): preferences.clear(); return Response(status_code=204)

    return application


load_project_env()
app = create_app(runner=environment_runner(), previewer=environment_previewer())
