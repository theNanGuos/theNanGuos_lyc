from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import socket
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel


class UnsafeMediaUrlError(ValueError): pass
class MediaTooLargeError(RuntimeError): pass


def safe_filename(value: str, fallback: str = "song") -> str:
    value = re.sub(r"[^\w\-. ]+", "_", Path(value).name, flags=re.UNICODE).strip(" ._")
    return value[:80] or fallback


class ArtifactStore:
    def __init__(self, outputs_dir: Path | str = "outputs", *, http_client: httpx.AsyncClient | None = None, max_media_bytes: int = 100 * 1024 * 1024, timeout_seconds: float = 60, resolver: Callable[[str, int], Awaitable[list[tuple]]] | None = None) -> None:
        self.outputs_dir = Path(outputs_dir)
        self._http = http_client
        self.max_media_bytes = max_media_bytes
        self.timeout_seconds = timeout_seconds
        self._resolver = resolver or self._resolve_host

    def request_dir(self, request_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", request_id):
            raise ValueError("invalid request_id")
        return self.outputs_dir / request_id

    def write_json(self, request_id: str, name: str, value: BaseModel | dict) -> Path:
        if name not in {"song_spec.json", "score_plan.json", "suno_request.json", "collaboration_log.json"}:
            raise ValueError("unsupported artifact name")
        root = self.request_dir(request_id)
        root.mkdir(parents=True, exist_ok=True)
        target = root / name
        temporary = target.with_suffix(target.suffix + ".tmp")
        data = value.model_dump(mode="json", by_alias=True) if isinstance(value, BaseModel) else value
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)
        return target

    async def download_media(self, request_id: str, kind: str, media_id: str, url: str, *, allowed_urls: set[str]) -> Path:
        parsed = urlparse(url)
        if url not in allowed_urls or parsed.scheme != "https" or not parsed.hostname:
            raise UnsafeMediaUrlError("media URL must be a recorded HTTPS URL")
        await self._validate_public_destination(parsed.hostname, parsed.port or 443)
        if kind not in {"audio", "covers"} or not re.fullmatch(r"[A-Za-z0-9_-]+", media_id):
            raise UnsafeMediaUrlError("invalid media destination")
        extension = ".mp3" if kind == "audio" else self._cover_extension(parsed.path)
        target = self.request_dir(request_id) / kind / f"{media_id}{extension}"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        total = 0
        try:
            if self._http is not None:
                context = self._http.stream("GET", url, timeout=self.timeout_seconds, follow_redirects=False)
            else:
                client = httpx.AsyncClient()
                context = client.stream("GET", url, timeout=self.timeout_seconds, follow_redirects=False)
            async with context as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.max_media_bytes:
                            raise MediaTooLargeError("media exceeds configured size limit")
                        output.write(chunk)
            os.replace(temporary, target)
            return target
        finally:
            if temporary.exists(): temporary.unlink()
            if self._http is None and "client" in locals(): await client.aclose()

    @staticmethod
    def _cover_extension(path: str) -> str:
        suffix = Path(path).suffix.lower()
        return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"

    @staticmethod
    async def _resolve_host(hostname: str, port: int) -> list[tuple]:
        return await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )

    async def _validate_public_destination(self, hostname: str, port: int) -> None:
        normalized = hostname.rstrip(".").lower()
        if normalized == "localhost" or normalized.endswith(".localhost"):
            raise UnsafeMediaUrlError("media URL destination is not public")
        try:
            literal = ipaddress.ip_address(normalized)
        except ValueError:
            try:
                addresses = await self._resolver(normalized, port)
            except (OSError, socket.gaierror) as exc:
                raise UnsafeMediaUrlError("media URL host could not be resolved safely") from exc
            if not addresses:
                raise UnsafeMediaUrlError("media URL host resolved to no addresses")
            candidates = []
            for address in addresses:
                try:
                    candidates.append(ipaddress.ip_address(address[4][0]))
                except (IndexError, TypeError, ValueError) as exc:
                    raise UnsafeMediaUrlError("media URL host returned an invalid address") from exc
        else:
            candidates = [literal]
        if any(not address.is_global for address in candidates):
            raise UnsafeMediaUrlError("media URL destination is not public")
