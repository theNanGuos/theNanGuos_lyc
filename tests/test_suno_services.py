import asyncio
import socket
import time
from pathlib import Path

import httpx
import pytest

from the_nanguos.schemas import SunoRequest
from the_nanguos.services import runtime as runtime_module
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.storage import ArtifactStore, UnsafeMediaUrlError
from the_nanguos.services.suno import SunoClient, SunoProtocolError, SunoTaskFailed


def request() -> SunoRequest:
    return SunoRequest.model_validate({
        "customMode": True, "instrumental": False, "model": "V5",
        "callBackUrl": "https://local.invalid/callback", "prompt": "[Verse]\nhello",
        "style": "dream pop", "title": "Night",
    })


def test_submit_and_poll_success_immediately() -> None:
    calls: list[str] = []
    async def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        if req.method == "POST":
            assert req.headers["Authorization"] == "Bearer token"
            assert b'"customMode":true' in req.content
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})
        return httpx.Response(200, json={"code": 200, "data": {
            "taskId": "task-1", "status": "SUCCESS", "response": {"sunoData": [{
                "id": "a1", "audio_url": "https://cdn.example/a.mp3",
                "image_url": "https://cdn.example/a.jpeg", "title": "Night",
            }]},
        }})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = SunoClient(api_key="token", base_url="https://api.example", http_client=http)
            task_id = await client.submit(request())
            return await client.poll(task_id, interval_seconds=0, timeout_seconds=1)
    details = asyncio.run(run())
    assert details.status == "SUCCESS" and details.audio_results[0].id == "a1"
    assert "record-info?taskId=task-1" in calls[1]


@pytest.mark.parametrize("status", ["CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"])
def test_failure_states_are_terminal(status: str) -> None:
    async def handler(req): return httpx.Response(200, json={"data": {"taskId": "x", "status": status}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            await SunoClient(api_key="x", http_client=http).poll("x", interval_seconds=0, timeout_seconds=1)
    with pytest.raises(SunoTaskFailed) as caught: asyncio.run(run())
    assert caught.value.status == status


def test_callback_failure_with_generated_audio_is_recovered_by_polling() -> None:
    async def handler(req):
        return httpx.Response(200, json={"data": {
            "taskId": "x",
            "status": "CALLBACK_EXCEPTION",
            "response": {"sunoData": [{
                "id": "a1",
                "audioUrl": "https://cdn.example/a.mp3",
                "imageUrl": "https://cdn.example/a.jpeg",
                "title": "Recovered",
            }]},
        }})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await SunoClient(api_key="x", http_client=http).poll(
                "x", interval_seconds=0, timeout_seconds=1
            )

    details = asyncio.run(run())
    assert details.status == "CALLBACK_EXCEPTION"
    assert details.audio_results[0].title == "Recovered"


def test_in_progress_details_ignore_incomplete_kie_candidates() -> None:
    async def handler(req):
        return httpx.Response(200, json={"data": {
            "taskId": "x",
            "status": "FIRST_SUCCESS",
            "response": {"sunoData": [{
                "id": "partial",
                "audioUrl": "",
                "streamAudioUrl": "",
                "imageUrl": "",
                "sourceAudioUrl": None,
                "sourceStreamAudioUrl": "https://source.example/partial",
                "sourceImageUrl": "https://source.example/partial.jpeg",
                "createTime": 1_700_000_000_000,
                "title": "Partial",
            }]},
        }})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await SunoClient(api_key="x", http_client=http).get_details("x")

    details = asyncio.run(run())
    assert details.status == "FIRST_SUCCESS"
    assert details.audio_results == []


def test_kie_success_accepts_source_urls_and_epoch_milliseconds() -> None:
    async def handler(req):
        return httpx.Response(200, json={"data": {
            "taskId": "x",
            "status": "SUCCESS",
            "response": {"sunoData": [{
                "id": "complete",
                "audioUrl": "https://cdn.example/complete.mp3",
                "streamAudioUrl": "https://cdn.example/complete",
                "imageUrl": "https://cdn.example/complete.jpeg",
                "sourceAudioUrl": "https://source.example/complete.mp3",
                "sourceStreamAudioUrl": "https://source.example/complete",
                "sourceImageUrl": "https://source.example/complete.jpeg",
                "createTime": 1_700_000_000_000,
                "title": "Complete",
            }]},
        }})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await SunoClient(api_key="x", http_client=http).get_details("x")

    audio = asyncio.run(run()).audio_results[0]
    assert audio.create_time == "2023-11-14T22:13:20+00:00"
    assert str(audio.source_audio_url) == "https://source.example/complete.mp3"


def test_remote_protocol_disconnect_is_retried() -> None:
    attempts = 0

    async def handler(req):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.RemoteProtocolError("server disconnected", request=req)
        return httpx.Response(200, json={"data": {"taskId": "x", "status": "PENDING"}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await SunoClient(api_key="x", http_client=http).get_details("x")

    assert asyncio.run(run()).status == "PENDING"
    assert attempts == 2


def test_environment_runner_prefers_kie_configuration(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("KIE_API_KEY", "kie-token")
    monkeypatch.setenv("KIE_BASE_URL", "https://api.kie.test")
    monkeypatch.setenv("KIE_CALLBACK_URL", "https://callback.invalid/kie/suno")
    monkeypatch.setenv("SUNO_API_KEY", "legacy-token")
    monkeypatch.setenv("SUNO_BASE_URL", "https://legacy.invalid")
    monkeypatch.setenv("SUNO_CALLBACK_URL", "https://legacy.invalid/callback")

    def fake_suno_client(**kwargs):
        captured.update(kwargs)
        return object()

    class FakeService:
        def __init__(self, **kwargs):
            pass

        async def __call__(self, record):
            return None

    monkeypatch.setattr(runtime_module, "SunoClient", fake_suno_client)
    monkeypatch.setattr(runtime_module, "DeepSeekLLMClient", lambda **kwargs: object())
    monkeypatch.setattr(runtime_module, "GenerationService", FakeService)
    record = GenerationRecord(request_id="kie-config", user_request="test")

    asyncio.run(runtime_module.environment_runner(outputs_dir=tmp_path)(record))

    assert captured == {"api_key": "kie-token", "base_url": "https://api.kie.test"}
    assert record.options["callback_url"] == "https://callback.invalid/kie/suno"


def test_environment_runner_keeps_legacy_suno_configuration_compatible(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    for name in ("KIE_API_KEY", "KIE_BASE_URL", "KIE_CALLBACK_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUNO_API_KEY", "legacy-token")
    monkeypatch.setenv("SUNO_BASE_URL", "https://legacy.example")
    monkeypatch.setenv("SUNO_CALLBACK_URL", "https://legacy.invalid/callback")

    def fake_suno_client(**kwargs):
        captured.update(kwargs)
        return object()

    class FakeService:
        def __init__(self, **kwargs):
            pass

        async def __call__(self, record):
            return None

    monkeypatch.setattr(runtime_module, "SunoClient", fake_suno_client)
    monkeypatch.setattr(runtime_module, "DeepSeekLLMClient", lambda **kwargs: object())
    monkeypatch.setattr(runtime_module, "GenerationService", FakeService)
    record = GenerationRecord(request_id="legacy-config", user_request="test")

    asyncio.run(runtime_module.environment_runner(outputs_dir=tmp_path)(record))

    assert captured == {"api_key": "legacy-token", "base_url": "https://legacy.example"}
    assert record.options["callback_url"] == "https://legacy.invalid/callback"


def test_poll_deadline_bounds_request_retries() -> None:
    calls = 0
    async def handler(req):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        raise httpx.ConnectError("offline", request=req)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = SunoClient(api_key="x", http_client=http, request_timeout=10)
            started = time.monotonic()
            with pytest.raises(TimeoutError):
                await client.poll("x", interval_seconds=0, timeout_seconds=0.02)
            return time.monotonic() - started
    elapsed = asyncio.run(run())
    assert elapsed < 0.1
    assert calls == 1


def test_unknown_and_empty_success_are_protocol_errors() -> None:
    responses = iter([{"data": {"taskId": "x", "status": "ALIEN"}}, {"data": {"taskId": "x", "status": "SUCCESS", "response": {"sunoData": []}}}])
    async def handler(req): return httpx.Response(200, json=next(responses))
    async def run_once(http):
        await SunoClient(api_key="x", http_client=http).poll("x", interval_seconds=0, timeout_seconds=1)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            for _ in range(2):
                with pytest.raises(SunoProtocolError): await run_once(http)
    asyncio.run(run())


def test_media_download_requires_recorded_https_and_is_atomic(tmp_path: Path) -> None:
    async def handler(req): return httpx.Response(200, content=b"abc", headers={"content-type": "audio/mpeg"})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async def public_resolver(hostname, port):
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
            store = ArtifactStore(tmp_path, http_client=http, max_media_bytes=10, resolver=public_resolver)
            path = await store.download_media("r1", "audio", "a1", "https://cdn.example/a.mp3", allowed_urls={"https://cdn.example/a.mp3"})
            assert path.read_bytes() == b"abc"
            with pytest.raises(UnsafeMediaUrlError):
                await store.download_media("r1", "audio", "a2", "http://evil/a.mp3", allowed_urls={"http://evil/a.mp3"})
    asyncio.run(run())


def test_media_download_retries_protocol_disconnect(tmp_path: Path) -> None:
    attempts = 0

    async def handler(req):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.RemoteProtocolError("server disconnected", request=req)
        return httpx.Response(200, content=b"complete", headers={"content-type": "audio/mpeg"})

    async def public_resolver(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            store = ArtifactStore(tmp_path, http_client=http, resolver=public_resolver)
            return await store.download_media(
                "r1",
                "audio",
                "a1",
                "https://cdn.example/a.mp3",
                allowed_urls={"https://cdn.example/a.mp3"},
            )

    path = asyncio.run(run())
    assert path.read_bytes() == b"complete"
    assert attempts == 2


@pytest.mark.parametrize("url", [
    "https://localhost/a.mp3",
    "https://127.0.0.1/a.mp3",
    "https://10.1.2.3/a.mp3",
    "https://169.254.1.1/a.mp3",
    "https://192.0.2.1/a.mp3",
    "https://[::1]/a.mp3",
])
def test_media_download_rejects_non_public_destinations(tmp_path: Path, url: str) -> None:
    async def handler(req):
        raise AssertionError("unsafe URL must be rejected before HTTP")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            store = ArtifactStore(tmp_path, http_client=http)
            with pytest.raises(UnsafeMediaUrlError):
                await store.download_media("r1", "audio", "a1", url, allowed_urls={url})
    asyncio.run(run())


def test_media_download_rejects_hostname_resolving_to_private_address(tmp_path: Path) -> None:
    async def private_resolver(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("172.16.0.5", port))]
    async def run():
        store = ArtifactStore(tmp_path, resolver=private_resolver)
        with pytest.raises(UnsafeMediaUrlError):
            await store.download_media("r1", "audio", "a1", "https://cdn.example/a.mp3", allowed_urls={"https://cdn.example/a.mp3"})
    asyncio.run(run())


def test_media_download_does_not_follow_redirects(tmp_path: Path) -> None:
    calls = 0
    async def handler(req):
        nonlocal calls
        calls += 1
        return httpx.Response(302, headers={"location": "https://127.0.0.1/secret"})
    async def public_resolver(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as http:
            store = ArtifactStore(tmp_path, http_client=http, resolver=public_resolver)
            with pytest.raises(httpx.HTTPStatusError):
                await store.download_media("r1", "audio", "a1", "https://cdn.example/a.mp3", allowed_urls={"https://cdn.example/a.mp3"})
    asyncio.run(run())
    assert calls == 1
