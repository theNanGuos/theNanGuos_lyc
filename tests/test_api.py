from pathlib import Path

from fastapi.testclient import TestClient

from the_nanguos.api.app import create_app
from the_nanguos.services.jobs import GenerationRecord
import pytest


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
    payload = GenerationRecord(request_id="r", user_request="x").public()
    assert "stop_event" not in payload and payload["request_id"] == "r"


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
