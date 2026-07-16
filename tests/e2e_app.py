from __future__ import annotations

import asyncio
import base64
import json
import tempfile
import uuid
from pathlib import Path

from the_nanguos.api.app import create_app
from the_nanguos.schemas import ConductorResult
from the_nanguos.services.jobs import GenerationRecord


RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="the-nanguos-e2e-"))
OUTPUTS_DIR = RUNTIME_ROOT / "outputs"
MEMORY_DIR = RUNTIME_ROOT / "memory"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def previewer(prompt: str, overrides: dict[str, object]) -> ConductorResult:
    return ConductorResult.model_validate(
        {
            "song_spec": {
                "title": "E2E 雨夜对话",
                "language": str(overrides.get("language") or "zh"),
                "genre": "jazz",
                "mood": ["warm", "restrained"],
                "duration_seconds": 90,
                "vocal": {"enabled": not bool(overrides.get("instrumental", False)), "gender": "female"},
                "tempo": {"bpm": 86, "feel": "laid-back"},
                "key": "C major",
                "structure": ["intro", "verse", "chorus", "outro"],
                "constraints": {"explicit": False, "avoid": ["heavy distortion"]},
            },
            "task_plan": {
                "goal": "Create an E2E test song",
                "steps": [
                    {
                        "id": "lyrics",
                        "actor": "LyricsAgent",
                        "task": "Write structured lyrics",
                        "output_key": "lyrics_result",
                    }
                ],
            },
        }
    )


def _finish(record: GenerationRecord) -> None:
    root = OUTPUTS_DIR / record.request_id
    audio_dir = root / "audio"
    cover_dir = root / "covers"
    audio_dir.mkdir(parents=True, exist_ok=True)
    cover_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "e2e-audio.mp3").write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")
    (cover_dir / "e2e-audio.png").write_bytes(PNG_BYTES)

    result = {
        "id": "e2e-audio",
        "title": "E2E 雨夜对话",
        "duration": 90,
        "modelName": "mock-v5",
        "tags": "neo soul, warm piano",
        "createTime": record.updated_at,
    }
    log = {
        "request_id": record.request_id,
        "user_request_summary": record.user_request,
        "artifacts": {"collaboration_log": "collaboration_log.json"},
        "steps": [],
        "validation": {"passed": True, "warnings": []},
        "suno": {
            "submitted": True,
            "task_id": record.task_id,
            "status": "SUCCESS",
            "audio_results": [result],
        },
    }
    (root / "collaboration_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    record.candidates = [
        {
            "audio_id": "e2e-audio",
            "title": result["title"],
            "duration": result["duration"],
            "audio_url": f"/api/generations/{record.request_id}/audio/e2e-audio",
            "download_url": f"/api/generations/{record.request_id}/audio/e2e-audio/download",
            "cover_url": f"/api/generations/{record.request_id}/cover/e2e-audio",
            "model_name": result["modelName"],
            "tags": result["tags"],
            "create_time": result["createTime"],
        }
    ]
    record.transition(status="completed", stage="completed", progress=100)


async def runner(record: GenerationRecord) -> None:
    if record.task_id is not None:
        _finish(record)
        return

    record.transition(status="running", stage="conductor", progress=5)
    record.transition(stage="lyrics", progress=20)
    record.transition(stage="music_planner", progress=35)
    record.transition(stage="arrangement", progress=50)
    record.task_id = f"mock-{record.request_id}"

    if "停止等待" in record.user_request:
        record.transition(stage="FIRST_SUCCESS", progress=80)
        await record.stop_event.wait()
        return

    await asyncio.sleep(0.05)
    _finish(record)


app = create_app(
    outputs_dir=OUTPUTS_DIR,
    memory_dir=MEMORY_DIR,
    runner=runner,
    previewer=previewer,
)


@app.post("/__e2e__/seed-interrupted")
async def seed_interrupted_generation() -> dict[str, str]:
    request_id = uuid.uuid4().hex
    root = OUTPUTS_DIR / request_id
    root.mkdir(parents=True, exist_ok=True)
    log = {
        "request_id": request_id,
        "user_request_summary": "E2E 服务重启恢复流程",
        "artifacts": {"collaboration_log": "collaboration_log.json"},
        "steps": [],
        "validation": {"passed": True, "warnings": []},
        "suno": {
            "submitted": True,
            "task_id": f"mock-restarted-{request_id}",
            "status": "PENDING",
            "audio_results": [],
        },
    }
    (root / "collaboration_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    app.state.registry.reindex()
    return {"request_id": request_id}
