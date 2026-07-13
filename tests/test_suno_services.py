import asyncio
import socket
import time
from pathlib import Path

import httpx
import pytest

from the_nanguos.schemas import SunoRequest
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
