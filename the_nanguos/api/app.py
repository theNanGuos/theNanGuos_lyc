from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from the_nanguos.memory import PreferenceStore
from the_nanguos.schemas import SunoModel, UserProfile
from the_nanguos.services.jobs import GenerationRecord, Runner, TaskRegistry
from the_nanguos.services.storage import safe_filename
from the_nanguos.services.runtime import environment_runner


GenerationWeight = Annotated[float, Field(ge=0, le=1, multiple_of=0.01)]


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


def create_app(*, outputs_dir: Path | str = "outputs", memory_dir: Path | str = "memory", runner: Runner | None = None) -> FastAPI:
    outputs = Path(outputs_dir)
    preferences = PreferenceStore(memory_dir)
    registry = TaskRegistry(outputs, runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        outputs.mkdir(parents=True, exist_ok=True)
        registry.reindex()
        app.state.registry = registry
        yield
        await registry.shutdown()

    application = FastAPI(title="theNanGuos", lifespan=lifespan)
    application.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

    @application.post("/api/generations", status_code=202)
    async def create_generation(payload: CreateGeneration):
        request_id = uuid.uuid4().hex
        override_data = payload.overrides.model_dump(mode="json", exclude_none=True)
        if payload.save_defaults:
            existing = preferences.load_defaults().model_dump(exclude={"schema_version"})
            existing.update({key: override_data[key] for key in payload.save_defaults if key in override_data})
            preferences.save_defaults(existing)
        record = GenerationRecord(request_id=request_id, user_request=payload.prompt, options=override_data)
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

    @application.post("/api/generations/{request_id}/stop-waiting")
    async def stop_waiting(request_id: str):
        record = registry.records.get(request_id)
        if record is None: raise HTTPException(404, "generation not found")
        record.stop_event.set(); record.status = "stopped"; record.stage = "stopped_waiting"
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
        record.stop_event = __import__("asyncio").Event(); record.status = "queued"; record.stage = "resume_polling"
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


app = create_app(runner=environment_runner())
