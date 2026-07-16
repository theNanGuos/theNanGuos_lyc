from pathlib import Path
import inspect
from importlib import import_module

from fastapi.testclient import TestClient

from the_nanguos.api.app import create_app
from the_nanguos.schemas import ConductorResult
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services import runtime as runtime_module
import pytest

api_module = import_module("the_nanguos.api.app")


def test_preferences_crud_does_not_remove_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    work = outputs / "keep"
    work.mkdir()
    (work / "x.txt").write_text("keep", encoding="utf-8")
    with TestClient(create_app(outputs_dir=outputs, memory_dir=tmp_path / "memory")) as client:
        assert client.put("/api/preferences/defaults", json={"language": "zh", "suno_model": "V5"}).status_code == 200
        assert client.put("/api/preferences/style", json={"markdown": "# warm"}).status_code == 200
        assert client.get("/api/preferences").json()["defaults"]["language"] == "zh"
        assert client.delete("/api/preferences").status_code == 204
    assert (work / "x.txt").exists()


def test_range_audio_and_safe_download_name(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    root = outputs / "r1"
    (root / "audio").mkdir(parents=True)
    (root / "audio" / "a1.mp3").write_bytes(b"0123456789")
    (root / "collaboration_log.json").write_text(
        '{"request_id":"r1","user_request_summary":"x","artifacts":{},"steps":[],"validation":{"passed":true,"warnings":[]},"suno":{"submitted":true,"task_id":"t","status":"SUCCESS","audio_results":[{"id":"a1","audio_url":"https://example/a","title":"../bad"}]}}',
        encoding="utf-8",
    )
    with TestClient(create_app(outputs_dir=outputs, memory_dir=tmp_path / "memory")) as client:
        response = client.get("/api/generations/r1/audio/a1", headers={"Range": "bytes=2-5"})
        assert response.status_code == 206 and response.content == b"2345"
        download = client.get("/api/generations/r1/audio/a1/download")
        assert download.status_code == 200
        assert "bad.mp3" in download.headers["content-disposition"] and ".." not in download.headers["content-disposition"]


def test_generation_record_public_omits_internal_event() -> None:
    record = GenerationRecord(request_id="r", user_request="x")
    record.transition(status="running", stage="lyrics", progress=20)

    payload = record.public()

    assert "stop_event" not in payload and payload["request_id"] == "r"
    assert payload["stage_events"][-1] == {
        "stage": "lyrics",
        "status": "running",
        "progress": 20,
        "at": record.updated_at,
    }


def test_generation_record_does_not_duplicate_same_stage_event() -> None:
    record = GenerationRecord(request_id="r", user_request="x")

    record.transition(status="running", stage="PENDING", progress=55)
    record.transition(status="running", stage="PENDING", progress=57)

    assert [event["stage"] for event in record.stage_events] == ["queued", "PENDING"]
    assert record.stage_events[-1]["progress"] == 57


def test_generation_record_public_exposes_only_safe_generation_settings() -> None:
    payload = GenerationRecord(
        request_id="r",
        user_request="x",
        options={
            "language": "zh",
            "instrumental": False,
            "vocal_gender": "f",
            "suno_model": "V5",
            "callback_url": "https://secret.example/callback",
        },
    ).public()

    assert payload["settings"] == {
        "language": "zh",
        "instrumental": False,
        "vocal_gender": "f",
        "suno_model": "V5",
    }
    assert "callback_url" not in str(payload)


@pytest.mark.parametrize("overrides", [
    {"unknown": "x"},
    {"vocal_gender": "female"},
    {"style_weight": 1.01},
    {"audio_weight": 0.555},
    {"callback_url": "https://attacker.example/callback"},
])
def test_create_generation_rejects_invalid_overrides(tmp_path: Path, overrides: dict) -> None:
    with TestClient(create_app(outputs_dir=tmp_path / "outputs", memory_dir=tmp_path / "memory")) as client:
        response = client.post("/api/generations", json={"prompt": "x", "overrides": overrides})
    assert response.status_code == 422


def test_create_generation_passes_valid_snake_case_overrides_to_runner(tmp_path: Path) -> None:
    received = []
    async def runner(record): received.append(record.options)
    payload = {"language":"zh", "instrumental":False, "vocal_gender":"m", "suno_model":"V5", "title":"Night", "custom_mode":True, "negative_tags":"noise", "style_weight":.55, "weirdness_constraint":.2, "audio_weight":.8}
    with TestClient(create_app(outputs_dir=tmp_path / "outputs", memory_dir=tmp_path / "memory", runner=runner)) as client:
        response = client.post("/api/generations", json={"prompt":"warm pop", "overrides":payload})
        assert response.status_code == 202
        client.get(f"/api/generations/{response.json()['request_id']}")
    assert received == [payload]


@pytest.mark.parametrize(("retention_limit", "expected"), [
    ("missing", 1),
    (1, 1),
    (2, 2),
    (None, None),
])
def test_create_generation_passes_local_retention_separately_from_suno_overrides(
    tmp_path: Path,
    retention_limit: object,
    expected: int | None,
) -> None:
    received: list[GenerationRecord] = []

    async def runner(record: GenerationRecord) -> None:
        received.append(record)

    payload: dict[str, object] = {"prompt": "warm pop", "overrides": {"suno_model": "V5"}}
    if retention_limit != "missing":
        payload["retention_limit"] = retention_limit
    with TestClient(create_app(outputs_dir=tmp_path / "outputs", memory_dir=tmp_path / "memory", runner=runner)) as client:
        response = client.post("/api/generations", json=payload)
        assert response.status_code == 202
        client.get(f"/api/generations/{response.json()['request_id']}")

    assert received[0].retention_limit == expected
    assert received[0].options == {"suno_model": "V5"}


@pytest.mark.parametrize("retention_limit", [0, 3, True, "1"])
def test_create_generation_rejects_invalid_local_retention(tmp_path: Path, retention_limit: object) -> None:
    with TestClient(create_app(outputs_dir=tmp_path / "outputs", memory_dir=tmp_path / "memory")) as client:
        response = client.post("/api/generations", json={"prompt": "warm pop", "retention_limit": retention_limit})

    assert response.status_code == 422


@pytest.mark.parametrize("status", ["completed", "failed", "stopped", "interrupted"])
def test_delete_generation_removes_entire_task_and_registry_record(tmp_path: Path, status: str) -> None:
    outputs = tmp_path / "outputs"
    task_dir = outputs / "delete-me"
    (task_dir / "audio").mkdir(parents=True)
    (task_dir / "audio" / "a.mp3").write_bytes(b"audio")
    application = create_app(outputs_dir=outputs, memory_dir=tmp_path / "memory")
    with TestClient(application) as client:
        application.state.registry.records["delete-me"] = GenerationRecord(
            request_id="delete-me", user_request="x", status=status
        )
        response = client.delete("/api/generations/delete-me")
        listed = client.get("/api/generations").json()["items"]

    assert response.status_code == 204
    assert not task_dir.exists()
    assert listed == []


@pytest.mark.parametrize("status", ["queued", "running"])
def test_delete_generation_rejects_active_task(tmp_path: Path, status: str) -> None:
    outputs = tmp_path / "outputs"
    task_dir = outputs / "active"
    task_dir.mkdir(parents=True)
    application = create_app(outputs_dir=outputs, memory_dir=tmp_path / "memory")
    with TestClient(application) as client:
        application.state.registry.records["active"] = GenerationRecord(
            request_id="active", user_request="x", status=status
        )
        response = client.delete("/api/generations/active")

    assert response.status_code == 409
    assert task_dir.exists()
    assert "active" in application.state.registry.records


def test_delete_generation_returns_404_and_keeps_record_on_file_failure(tmp_path: Path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    task_dir = outputs / "locked"
    task_dir.mkdir(parents=True)
    application = create_app(outputs_dir=outputs, memory_dir=tmp_path / "memory")
    with TestClient(application) as client:
        missing = client.delete("/api/generations/missing")
        application.state.registry.records["locked"] = GenerationRecord(
            request_id="locked", user_request="x", status="completed"
        )

        async def fail_delete(request_id: str) -> None:
            raise OSError("private filesystem detail")

        monkeypatch.setattr(application.state.registry, "delete", fail_delete, raising=False)
        failed = client.delete("/api/generations/locked")

    assert missing.status_code == 404
    assert failed.status_code == 500
    assert failed.json()["detail"] == "作品文件删除失败，请关闭占用文件后重试"
    assert "locked" in application.state.registry.records
    assert task_dir.exists()


def test_generation_preview_reports_unavailable_service(tmp_path: Path) -> None:
    with TestClient(create_app(outputs_dir=tmp_path / "outputs", memory_dir=tmp_path / "memory")) as client:
        response = client.post("/api/generation-previews", json={"prompt": "warm jazz"})

    assert response.status_code == 503
    assert response.json()["detail"] == "generation preview unavailable"


def test_create_app_accepts_generation_previewer_dependency() -> None:
    assert "previewer" in inspect.signature(create_app).parameters


def test_runtime_provides_environment_generation_previewer() -> None:
    assert hasattr(runtime_module, "environment_previewer")


def test_generation_preview_returns_conductor_plan(tmp_path: Path) -> None:
    received: list[tuple[str, dict[str, object]]] = []

    async def previewer(prompt: str, overrides: dict[str, object]) -> ConductorResult:
        received.append((prompt, overrides))
        return ConductorResult.model_validate({
            "song_spec": {
                "title": "Rain Dialogue",
                "language": "zh",
                "genre": "jazz",
                "mood": ["warm"],
                "duration_seconds": 120,
                "structure": ["verse", "chorus"],
            },
            "task_plan": {
                "goal": "create warm jazz",
                "steps": [{
                    "id": "lyrics",
                    "actor": "LyricsAgent",
                    "task": "write lyrics",
                    "output_key": "lyrics_result",
                }],
            },
        })

    with TestClient(create_app(
        outputs_dir=tmp_path / "outputs",
        memory_dir=tmp_path / "memory",
        previewer=previewer,
    )) as client:
        response = client.post("/api/generation-previews", json={
            "prompt": "warm jazz",
            "overrides": {"language": "en", "instrumental": True, "vocal_gender": "m", "title": "User title"},
        })

    assert response.status_code == 200
    body = response.json()
    assert len(body["preview_id"]) == 32
    assert body["song_spec"]["genre"] == "jazz"
    assert body["song_spec"]["title"] == "User title"
    assert body["song_spec"]["language"] == "en"
    assert body["song_spec"]["vocal"] == {"enabled": False, "gender": None}
    assert body["task_plan"]["steps"][0]["actor"] == "LyricsAgent"
    assert received == [("warm jazz", {"language": "en", "instrumental": True, "vocal_gender": "m", "title": "User title"})]


def test_generation_consumes_approved_preview_once(tmp_path: Path) -> None:
    generated: list[GenerationRecord] = []

    async def runner(record: GenerationRecord) -> None:
        generated.append(record)

    async def previewer(prompt: str, overrides: dict[str, object]) -> ConductorResult:
        return ConductorResult.model_validate({
            "song_spec": {
                "title": "Initial title",
                "language": "zh",
                "genre": "jazz",
                "mood": ["warm"],
                "duration_seconds": 120,
                "structure": ["verse", "chorus"],
            },
            "task_plan": {
                "goal": "create warm jazz",
                "steps": [{
                    "id": "lyrics",
                    "actor": "LyricsAgent",
                    "task": "write lyrics",
                    "output_key": "lyrics_result",
                }],
            },
        })

    with TestClient(create_app(
        outputs_dir=tmp_path / "outputs",
        memory_dir=tmp_path / "memory",
        runner=runner,
        previewer=previewer,
    )) as client:
        preview = client.post("/api/generation-previews", json={"prompt": "warm jazz"}).json()
        approved = dict(preview["song_spec"])
        approved["title"] = "User approved title"
        payload = {
            "prompt": "warm jazz",
            "preview_id": preview["preview_id"],
            "approved_song_spec": approved,
        }
        created = client.post("/api/generations", json=payload)
        repeated = client.post("/api/generations", json=payload)

    assert created.status_code == 202
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "generation preview unavailable or already used"
    assert len(generated) == 1
    assert generated[0].approved_song_spec.title == "User approved title"
    assert generated[0].approved_task_plan.goal == "create warm jazz"


def test_generation_preview_expires_after_thirty_minutes(tmp_path: Path, monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(api_module, "_monotonic", lambda: now[0], raising=False)

    async def previewer(prompt: str, overrides: dict[str, object]) -> ConductorResult:
        return ConductorResult.model_validate({
            "song_spec": {
                "title": "Night",
                "language": "zh",
                "genre": "jazz",
                "mood": ["warm"],
                "duration_seconds": 120,
                "structure": ["verse"],
            },
            "task_plan": {
                "goal": "create jazz",
                "steps": [{
                    "id": "lyrics",
                    "actor": "LyricsAgent",
                    "task": "write",
                    "output_key": "lyrics_result",
                }],
            },
        })

    with TestClient(create_app(
        outputs_dir=tmp_path / "outputs",
        memory_dir=tmp_path / "memory",
        runner=lambda record: None,
        previewer=previewer,
    )) as client:
        preview = client.post("/api/generation-previews", json={"prompt": "jazz"}).json()
        now[0] += 1801
        response = client.post("/api/generations", json={
            "prompt": "jazz",
            "preview_id": preview["preview_id"],
            "approved_song_spec": preview["song_spec"],
        })

    assert response.status_code == 409
