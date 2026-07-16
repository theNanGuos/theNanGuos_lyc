from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Awaitable, Callable

from the_nanguos.schemas import SongSpec, TaskPlan
from the_nanguos.services.storage import ArtifactStore


@dataclass
class GenerationRecord:
    request_id: str
    user_request: str
    status: str = "queued"
    stage: str = "queued"
    progress: int = 0
    task_id: str | None = None
    error: dict[str, object] | None = None
    candidates: list[dict[str, object]] = field(default_factory=list)
    stage_events: list[dict[str, object]] = field(default_factory=list)
    options: dict[str, object] = field(default_factory=dict)
    retention_limit: int | None = 1
    approved_song_spec: SongSpec | None = field(default=None, repr=False)
    approved_task_plan: TaskPlan | None = field(default=None, repr=False)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    stop_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def __post_init__(self) -> None:
        if not self.stage_events:
            self.stage_events.append(
                {
                    "stage": self.stage,
                    "status": self.status,
                    "progress": self.progress,
                    "at": self.updated_at,
                }
            )

    def transition(self, *, status: str | None = None, stage: str, progress: int) -> None:
        timestamp = datetime.now(UTC).isoformat()
        if status is not None:
            self.status = status
        self.stage = stage
        self.progress = progress
        self.updated_at = timestamp
        event = {
            "stage": self.stage,
            "status": self.status,
            "progress": self.progress,
            "at": timestamp,
        }
        if self.stage_events and self.stage_events[-1]["stage"] == stage:
            self.stage_events[-1] = event
        else:
            self.stage_events.append(event)

    def public(self) -> dict[str, object]:
        safe_setting_names = ("language", "instrumental", "vocal_gender", "suno_model")
        settings = {name: self.options[name] for name in safe_setting_names if name in self.options}
        return {"request_id": self.request_id, "user_request": self.user_request, "status": self.status, "stage": self.stage, "progress": self.progress, "task_id": self.task_id, "error": self.error, "candidates": self.candidates, "settings": settings, "retention_limit": self.retention_limit, "stage_events": self.stage_events, "created_at": self.created_at, "updated_at": self.updated_at}


Runner = Callable[[GenerationRecord], Awaitable[None]]


class TaskRegistry:
    def __init__(self, outputs_dir: Path | str = "outputs", runner: Runner | None = None) -> None:
        self.outputs_dir = Path(outputs_dir)
        self.runner = runner
        self.records: dict[str, GenerationRecord] = {}
        self.tasks: dict[str, asyncio.Task[None]] = {}

    def reindex(self) -> None:
        if not self.outputs_dir.exists(): return
        for log_path in self.outputs_dir.glob("*/collaboration_log.json"):
            try:
                log = json.loads(log_path.read_text(encoding="utf-8"))
                request_id = log["request_id"]
                suno = log.get("suno", {})
                remote = suno.get("status")
                if remote == "SUCCESS": status, stage, progress = "completed", "completed", 100
                elif remote in {"PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"}:
                    status, stage, progress = "interrupted", "service_restarted", 60
                elif remote in {"STOPPED_WAITING"}:
                    status, stage, progress = "stopped", "stopped_waiting", 60
                else: status, stage, progress = "failed", "failed", 100
                candidates = []
                for item in suno.get("audio_results", []):
                    audio_id = item.get("id")
                    if not audio_id: continue
                    candidates.append({
                        "audio_id": audio_id, "title": item.get("title") or "song", "duration": item.get("duration"),
                        "audio_url": f"/api/generations/{request_id}/audio/{audio_id}",
                        "download_url": f"/api/generations/{request_id}/audio/{audio_id}/download",
                        "cover_url": f"/api/generations/{request_id}/cover/{audio_id}",
                        "model_name": item.get("modelName"),
                        "tags": item.get("tags"),
                        "create_time": item.get("createTime"),
                    })
                retention_limit = suno.get("retention_limit") if "retention_limit" in suno else None
                self.records[request_id] = GenerationRecord(request_id=request_id, user_request=log.get("user_request_summary", ""), status=status, stage=stage, progress=progress, task_id=suno.get("task_id"), candidates=candidates, retention_limit=retention_limit)
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def start(self, record: GenerationRecord) -> None:
        self.records[record.request_id] = record
        if self.runner is not None:
            self.tasks[record.request_id] = asyncio.create_task(self._run(record))

    async def delete(self, request_id: str) -> None:
        record = self.records.get(request_id)
        if record is None:
            raise KeyError(request_id)
        task = self.tasks.get(request_id)
        if record.status in {"queued", "running"} or (task is not None and not task.done()):
            raise RuntimeError("active generation cannot be deleted")
        await asyncio.to_thread(ArtifactStore(self.outputs_dir).delete_request, request_id)
        self.records.pop(request_id, None)
        self.tasks.pop(request_id, None)

    async def _run(self, record: GenerationRecord) -> None:
        try:
            await self.runner(record)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if record.status != "stopped":
                record.transition(status="failed", stage="failed", progress=100)
                record.error = {"code": type(exc).__name__, "message": str(exc)}
                self._persist_failure(record)
        finally:
            record.updated_at = datetime.now(UTC).isoformat()

    def _persist_failure(self, record: GenerationRecord) -> None:
        root = self.outputs_dir / record.request_id
        root.mkdir(parents=True, exist_ok=True)
        path = root / "collaboration_log.json"
        try:
            if path.exists(): data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = {"request_id":record.request_id, "user_request_summary":record.user_request, "artifacts":{"collaboration_log":"collaboration_log.json"}, "steps":[], "validation":{"passed":False,"warnings":[]}, "suno":{"submitted":bool(record.task_id), "task_id":record.task_id, "audio_results":[]}}
            data["suno"]["status"] = "FAILED"
            data["suno"]["error"] = record.error
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        except (OSError, ValueError, TypeError, KeyError):
            return

    async def shutdown(self) -> None:
        active = [task for task in self.tasks.values() if not task.done()]
        for task in active: task.cancel()
        if active: await asyncio.gather(*active, return_exceptions=True)
