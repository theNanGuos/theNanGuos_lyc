from __future__ import annotations

import json
from typing import Protocol, Sequence, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class StructuredGenerationError(RuntimeError):
    def __init__(self, message: str, *, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


class LLMClient(Protocol):
    async def generate_structured(
        self,
        *,
        messages: Sequence[dict[str, str]],
        response_model: type[T],
    ) -> T: ...


class DeepSeekLLMClient:
    """DeepSeek OpenAI-compatible structured output adapter.

    The adapter intentionally reads only final message.content. Provider
    reasoning fields are neither exposed nor retained.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 90,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._http_client = http_client
        self._max_retries = max_retries
        self._timeout = timeout_seconds

    async def generate_structured(
        self,
        *,
        messages: Sequence[dict[str, str]],
        response_model: type[T],
    ) -> T:
        last_error = "empty response"
        total_attempts = self._max_retries + 1
        for attempt in range(1, total_attempts + 1):
            try:
                content = await self._request_content(messages)
                if not content or not content.strip():
                    raise ValueError("empty JSON content")
                return response_model.model_validate(json.loads(content))
            except (ValueError, json.JSONDecodeError, ValidationError, KeyError, IndexError, TypeError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        raise StructuredGenerationError(
            f"structured generation failed after {total_attempts} attempts: {last_error}",
            attempts=total_attempts,
        )

    async def _request_content(self, messages: Sequence[dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": list(messages),
            "response_format": {"type": "json_object"},
            # Equivalent to OpenAI SDK's extra_body={"thinking": ...}; with
            # direct HTTP the provider extension belongs at the top level.
            "thinking": {"type": "enabled"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        if self._http_client is not None:
            response = await self._http_client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers, timeout=self._timeout
            )
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers, timeout=self._timeout
                )
        response.raise_for_status()
        data = response.json()
        if data["choices"][0].get("finish_reason") == "length":
            raise ValueError("structured response was truncated")
        # Deliberately do not bind, copy, return, or log reasoning_content.
        return data["choices"][0]["message"].get("content") or ""
