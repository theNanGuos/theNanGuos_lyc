import asyncio
from collections import deque
import json
from pathlib import Path
import socket

from the_nanguos.services.generation import GenerationService
import the_nanguos.services.generation as generation_module
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.storage import ArtifactStore
from the_nanguos.services.suno import SunoTaskFailed
from the_nanguos.tools.suno_request_builder import build_suno_request
from the_nanguos.schemas import CollaborationLog, SongSpec, SunoAudio, SunoTaskDetails, TaskPlan
from the_nanguos.services.suno import SunoPollingStopped
import httpx
import pytest


def test_all_kie_audio_urls_are_sanitized_before_logging() -> None:
    audio = SunoAudio.model_validate({
        "id": "a1",
        "audioUrl": "https://cdn.example/a.mp3?token=secret",
        "streamAudioUrl": "https://cdn.example/a?token=secret",
        "imageUrl": "https://cdn.example/a.jpeg?token=secret",
        "sourceAudioUrl": "https://source.example/a.mp3?token=secret",
        "sourceStreamAudioUrl": "https://source.example/a?token=secret",
        "sourceImageUrl": "https://source.example/a.jpeg?token=secret",
        "title": "A",
    })

    sanitized = generation_module._sanitized_audio(audio)

    for value in (
        sanitized.audio_url,
        sanitized.stream_audio_url,
        sanitized.image_url,
        sanitized.source_audio_url,
        sanitized.source_stream_audio_url,
        sanitized.source_image_url,
    ):
        assert value is not None
        assert "?" not in str(value)


class FakeLLM:
    def __init__(self):
        self.results = deque([
            {"song_spec": {"title":"Night","language":"zh","genre":"pop","mood":["warm"],"duration_seconds":60,"structure":["verse"]}, "task_plan":{"goal":"x","steps":[{"id":"lyrics","actor":"LyricsAgent","task":"x","output_key":"lyrics_result"}]}},
            {"sections":[{"name":"verse","lines":["hello"]}]},
            {"bpm":90,"key":"C major","sections":[{"name":"verse","duration_seconds":60,"chords":["C"],"melody_intent":"soft"}]},
            {"instruments":["piano"],"mix_style":"warm","dynamic_curve":"rise","suno_style":"warm pop","sections":[{"name":"verse","arrangement":"piano"}]},
        ])
    async def generate_structured(self, *, messages, response_model): return response_model.model_validate(self.results.popleft())


class ApprovedPlanLLM:
    def __init__(self):
        self.calls = 0
        self.results = deque([
            {"sections":[{"name":"verse","lines":["hello"]}]},
            {"bpm":90,"key":"C major","sections":[{"name":"verse","duration_seconds":60,"chords":["C"],"melody_intent":"soft"}]},
            {"instruments":["piano"],"mix_style":"warm","dynamic_curve":"rise","suno_style":"warm jazz","sections":[{"name":"verse","arrangement":"piano"}]},
        ])

    async def generate_structured(self, *, messages, response_model):
        self.calls += 1
        return response_model.model_validate(self.results.popleft())


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


def test_approved_preview_skips_conductor_in_generation_graph(tmp_path: Path) -> None:
    llm = ApprovedPlanLLM()
    record = GenerationRecord(
        request_id="approved-preview",
        user_request="warm jazz",
        options={"callback_url":"https://local.invalid/callback", "suno_model":"V5", "title":"Initial override"},
        approved_song_spec=SongSpec.model_validate({
            "title":"User approved",
            "language":"zh",
            "genre":"jazz",
            "mood":["warm"],
            "duration_seconds":60,
            "structure":["verse"],
        }),
        approved_task_plan=TaskPlan.model_validate({
            "goal":"approved goal",
            "steps":[{"id":"lyrics","actor":"LyricsAgent","task":"write","output_key":"lyrics_result"}],
        }),
    )

    asyncio.run(GenerationService(llm=llm, artifact_store=ArtifactStore(tmp_path), submit=False)(record))

    assert llm.calls == 3
    artifact = __import__("json").loads((tmp_path / "approved-preview" / "song_spec.json").read_text(encoding="utf-8"))
    assert artifact["title"] == "User approved"


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
    assert [event["stage"] for event in record.stage_events] == [
        "queued",
        "conductor",
        "lyrics",
        "music_planner",
        "arrangement",
        "suno_submit",
        "PENDING",
        "TEXT_SUCCESS",
        "FIRST_SUCCESS",
    ]


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
            return SunoTaskDetails.model_validate({"taskId":"old-task", "status":"SUCCESS", "response":{"sunoData":[{"id":"a1", "audioUrl":"https://cdn.example/a.mp3", "title":"Night", "modelName":"chirp-v5", "tags":"jazz, warm", "createTime":"2026-07-14T12:34:56Z"}]}})
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
    assert record.candidates[0]["audio_id"] == "a1"
    assert record.candidates[0]["model_name"] == "chirp-v5"
    assert record.candidates[0]["tags"] == "jazz, warm"
    assert record.candidates[0]["create_time"] == "2026-07-14T12:34:56Z"


@pytest.mark.parametrize(("retention_limit", "expected_ids"), [
    (1, ["a1"]),
    (2, ["a1", "a2"]),
    (None, ["a1", "a2", "a3"]),
])
def test_generation_retains_only_selected_local_candidates_and_logs_counts(
    tmp_path: Path,
    retention_limit: int | None,
    expected_ids: list[str],
) -> None:
    class NeverLLM:
        async def generate_structured(self, **kwargs):
            raise AssertionError("agents must not run on resume")

    class ThreeCandidateSuno:
        async def submit(self, request):
            raise AssertionError("resume must not submit")

        async def poll(self, task_id, **kwargs):
            return SunoTaskDetails.model_validate({
                "taskId": task_id,
                "status": "SUCCESS",
                "response": {"sunoData": [
                    {"id": f"a{index}", "audioUrl": f"https://cdn.example/a{index}.mp3?token=secret-{index}", "title": f"Song {index}"}
                    for index in range(1, 4)
                ]},
            })

    async def media(_request):
        return httpx.Response(200, content=b"mp3")

    async def public_resolver(_hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    async def run() -> GenerationRecord:
        async with httpx.AsyncClient(transport=httpx.MockTransport(media)) as http:
            store = ArtifactStore(tmp_path, http_client=http, resolver=public_resolver)
            record = GenerationRecord(
                request_id=f"retain-{retention_limit}",
                user_request="x",
                stage="resume_polling",
                task_id="old-task",
                retention_limit=retention_limit,
            )
            store.write_json(record.request_id, "collaboration_log.json", CollaborationLog(request_id=record.request_id, user_request_summary="x"))
            await GenerationService(llm=NeverLLM(), artifact_store=store, suno=ThreeCandidateSuno())(record)
            return record

    record = asyncio.run(run())
    log_path = tmp_path / record.request_id / "collaboration_log.json"
    log_data = json.loads(log_path.read_text(encoding="utf-8"))

    assert [candidate["audio_id"] for candidate in record.candidates] == expected_ids
    assert sorted(path.stem for path in (tmp_path / record.request_id / "audio").glob("*.mp3")) == expected_ids
    assert log_data["suno"]["provider_candidate_count"] == 3
    assert log_data["suno"]["retention_limit"] == retention_limit
    assert log_data["suno"]["retained_candidate_count"] == len(expected_ids)
    assert [item["id"] for item in log_data["suno"]["audio_results"]] == expected_ids
    for discarded in {"a1", "a2", "a3"} - set(expected_ids):
        assert f"/{discarded}.mp3" not in log_path.read_text(encoding="utf-8")


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
