import asyncio
from collections import deque
from pathlib import Path
import socket

from the_nanguos.services.generation import GenerationService
import the_nanguos.services.generation as generation_module
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.storage import ArtifactStore
from the_nanguos.services.suno import SunoTaskFailed
from the_nanguos.tools.suno_request_builder import build_suno_request
from the_nanguos.schemas import CollaborationLog, SunoTaskDetails
from the_nanguos.services.suno import SunoPollingStopped
import httpx


class FakeLLM:
    def __init__(self):
        self.results = deque([
            {"song_spec": {"title":"Night","language":"zh","genre":"pop","mood":["warm"],"duration_seconds":60,"structure":["verse"]}, "task_plan":{"goal":"x","steps":[{"id":"lyrics","actor":"LyricsAgent","task":"x","output_key":"lyrics_result"}]}},
            {"sections":[{"name":"verse","lines":["hello"]}]},
            {"bpm":90,"key":"C major","sections":[{"name":"verse","duration_seconds":60,"chords":["C"],"melody_intent":"soft"}]},
            {"instruments":["piano"],"mix_style":"warm","dynamic_curve":"rise","suno_style":"warm pop","sections":[{"name":"verse","arrangement":"piano"}]},
        ])
    async def generate_structured(self, *, messages, response_model): return response_model.model_validate(self.results.popleft())


def test_no_submit_pipeline_writes_four_json_artifacts(tmp_path: Path) -> None:
    record = GenerationRecord(request_id="r1", user_request="warm pop", options={"callback_url":"https://local.invalid/callback", "suno_model":"V5"})
    service = GenerationService(llm=FakeLLM(), artifact_store=ArtifactStore(tmp_path), submit=False)
    asyncio.run(service(record))
    assert record.status == "completed"
    assert {path.name for path in (tmp_path / "r1").glob("*.json")} == {"song_spec.json", "score_plan.json", "suno_request.json", "collaboration_log.json"}


def test_explicit_title_overrides_llm_title_in_artifacts_and_suno_request(tmp_path: Path) -> None:
    record = GenerationRecord(
        request_id="title-override",
        user_request="warm pop",
        options={
            "callback_url": "https://local.invalid/callback",
            "suno_model": "V5",
            "title": "用户指定标题",
        },
    )
    asyncio.run(GenerationService(llm=FakeLLM(), artifact_store=ArtifactStore(tmp_path), submit=False)(record))

    import json

    request_dir = tmp_path / "title-override"
    song_spec = json.loads((request_dir / "song_spec.json").read_text(encoding="utf-8"))
    suno_request = json.loads((request_dir / "suno_request.json").read_text(encoding="utf-8"))
    assert song_spec["title"] == "用户指定标题"
    assert suno_request["title"] == "用户指定标题"


def test_generation_exposes_exact_suno_stage_and_anchor_progress(tmp_path: Path) -> None:
    snapshots: list[tuple[str, int]] = []

    class StageSuno:
        async def submit(self, request):
            return "task-stage"

        async def poll(self, task_id, *, on_update, **kwargs):
            for status in ("PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"):
                await on_update(SunoTaskDetails(task_id=task_id, status=status))
                snapshots.append((record.stage, record.progress))
            raise SunoPollingStopped("test completed after observing stages")

    record = GenerationRecord(
        request_id="stage-progress",
        user_request="warm pop",
        options={"callback_url": "https://local.invalid/callback", "suno_model": "V5"},
    )

    with __import__("pytest").raises(SunoPollingStopped):
        asyncio.run(
            GenerationService(
                llm=FakeLLM(),
                artifact_store=ArtifactStore(tmp_path),
                suno=StageSuno(),
            )(record)
        )

    assert snapshots == [("PENDING", 55), ("TEXT_SUCCESS", 65), ("FIRST_SUCCESS", 80)]


def test_generation_service_enters_compiled_langgraph(tmp_path: Path, monkeypatch) -> None:
    calls = 0
    real_builder = generation_module.build_generate_song_graph if hasattr(generation_module, "build_generate_song_graph") else None
    def tracked_builder(*args, **kwargs):
        nonlocal calls
        calls += 1
        assert real_builder is not None
        return real_builder(*args, **kwargs)
    monkeypatch.setattr(generation_module, "build_generate_song_graph", tracked_builder, raising=False)
    record = GenerationRecord(request_id="r2", user_request="warm pop", options={"callback_url":"https://local.invalid/callback", "suno_model":"V5"})
    asyncio.run(GenerationService(llm=FakeLLM(), artifact_store=ArtifactStore(tmp_path), submit=False)(record))
    assert calls == 1


def test_resume_enters_poll_and_save_without_agents_or_submit(tmp_path: Path) -> None:
    class NeverLLM:
        async def generate_structured(self, **kwargs): raise AssertionError("agents must not run on resume")
    class ResumeSuno:
        async def submit(self, request): raise AssertionError("resume must not submit a new task")
        async def poll(self, task_id, **kwargs):
            assert task_id == "old-task"
            return SunoTaskDetails.model_validate({"taskId":"old-task", "status":"SUCCESS", "response":{"sunoData":[{"id":"a1", "audioUrl":"https://cdn.example/a.mp3", "title":"Night"}]}})
    async def media(req): return httpx.Response(200, content=b"mp3")
    async def public_resolver(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(media)) as http:
            store = ArtifactStore(tmp_path, http_client=http, resolver=public_resolver)
            store.write_json("r3", "collaboration_log.json", CollaborationLog(request_id="r3", user_request_summary="x"))
            record = GenerationRecord(request_id="r3", user_request="x", stage="resume_polling", task_id="old-task")
            await GenerationService(llm=NeverLLM(), artifact_store=store, suno=ResumeSuno())(record)
            return record
    record = asyncio.run(run())
    assert record.status == "completed" and (tmp_path / "r3" / "audio" / "a1.mp3").exists()


def test_failed_suno_terminal_status_is_persisted(tmp_path: Path) -> None:
    class FailedSuno:
        async def submit(self, request): return "failed-task"
        async def poll(self, task_id, **kwargs):
            raise SunoTaskFailed(task_id, "GENERATE_AUDIO_FAILED")
    record = GenerationRecord(request_id="r4", user_request="warm pop", options={"suno_model":"V5"})
    service = GenerationService(llm=FakeLLM(), artifact_store=ArtifactStore(tmp_path), suno=FailedSuno())
    try:
        asyncio.run(service(record))
    except SunoTaskFailed:
        pass
    else:
        raise AssertionError("failed terminal status must stop generation")
    log = CollaborationLog.model_validate_json((tmp_path / "r4" / "collaboration_log.json").read_text(encoding="utf-8"))
    assert log.suno.status == "GENERATE_AUDIO_FAILED"
    assert log.suno.last_status == "GENERATE_AUDIO_FAILED"
