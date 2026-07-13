from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from the_nanguos.schemas import SunoAudio, SunoRequest, SunoTaskDetails

IN_PROGRESS = {"PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"}
FAILED = {"CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"}


class SunoError(RuntimeError): pass
class SunoProtocolError(SunoError): pass
class SunoTaskFailed(SunoError):
    def __init__(self, task_id: str, status: str) -> None:
        self.task_id = task_id
        self.status = status
        super().__init__(f"Suno task {task_id} failed with {status}")
class SunoPollingStopped(SunoError): pass


class SunoClient:
    def __init__(self, *, api_key: str, base_url: str = "https://api.sunoapi.org", http_client: httpx.AsyncClient | None = None, request_timeout: float = 30) -> None:
        if not api_key:
            raise ValueError("SUNO_API_KEY is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client
        self._timeout = request_timeout

    async def submit(self, request: SunoRequest) -> str:
        data = await self._request("POST", "/api/v1/generate", json=request.model_dump(mode="json", by_alias=True, exclude_none=True))
        task_id = data.get("data", {}).get("taskId")
        if not isinstance(task_id, str) or not task_id:
            raise SunoProtocolError("Suno submit response omitted data.taskId")
        return task_id

    async def get_details(self, task_id: str) -> SunoTaskDetails:
        payload = await self._request("GET", "/api/v1/generate/record-info", params={"taskId": task_id})
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            raise SunoProtocolError("Suno details response omitted data.status")
        status = data["status"]
        if status not in IN_PROGRESS | FAILED | {"SUCCESS"}:
            raise SunoProtocolError(f"unknown Suno status: {status}")
        if status in FAILED:
            raise SunoTaskFailed(task_id, status)
        raw_audio = data.get("response", {}).get("sunoData") if isinstance(data.get("response"), dict) else None
        if status == "SUCCESS" and (not isinstance(raw_audio, list) or not raw_audio):
            raise SunoProtocolError("SUCCESS response contains no sunoData")
        audio = [SunoAudio.model_validate(item) for item in (raw_audio or [])]
        return SunoTaskDetails(task_id=data.get("taskId") or task_id, status=status, audio_results=audio)

    async def poll(self, task_id: str, *, interval_seconds: float = 30, timeout_seconds: float = 1200, stop_event: asyncio.Event | None = None, on_update=None) -> SunoTaskDetails:
        deadline = time.monotonic() + timeout_seconds
        while True:
            if stop_event and stop_event.is_set():
                raise SunoPollingStopped("local polling stopped; remote task may continue")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Suno polling exceeded {timeout_seconds} seconds")
            try:
                # The deadline encloses the whole request, including all transient
                # retries performed by _request, rather than only the sleep gap.
                details = await asyncio.wait_for(self.get_details(task_id), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"Suno polling exceeded {timeout_seconds} seconds") from exc
            if on_update is not None:
                result = on_update(details)
                if hasattr(result, "__await__"):
                    await result
            if details.status == "SUCCESS":
                return details
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Suno polling exceeded {timeout_seconds} seconds")
            if interval_seconds:
                try:
                    await asyncio.wait_for(asyncio.sleep(min(interval_seconds, remaining)), timeout=remaining)
                except asyncio.TimeoutError as exc:
                    raise TimeoutError(f"Suno polling exceeded {timeout_seconds} seconds") from exc

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        transient: Exception | None = None
        for attempt in range(3):
            try:
                if self._http is not None:
                    response = await self._http.request(method, f"{self._base_url}{path}", headers=headers, timeout=self._timeout, **kwargs)
                else:
                    async with httpx.AsyncClient() as client:
                        response = await client.request(method, f"{self._base_url}{path}", headers=headers, timeout=self._timeout, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError("transient Suno response", request=response.request, response=response)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise SunoProtocolError("Suno response must be a JSON object")
                return data
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500 and exc.response.status_code != 429:
                    raise
                transient = exc
                if attempt < 2:
                    await asyncio.sleep(0)
        raise SunoError(f"Suno request failed after retries: {type(transient).__name__}") from transient
