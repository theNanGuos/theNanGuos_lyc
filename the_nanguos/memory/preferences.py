from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Mapping

from the_nanguos.schemas import UserProfile

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.RLock] = {}


def _lock_for(path: Path) -> threading.RLock:
    key = path.resolve()
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


class PreferenceStore:
    """Single-process preference store; writes only on explicit method calls."""

    def __init__(self, memory_dir: Path | str = "memory") -> None:
        self.memory_dir = Path(memory_dir)
        self.profile_path = self.memory_dir / "user_profile.json"
        self.style_path = self.memory_dir / "style_preferences.md"
        self._lock = _lock_for(self.memory_dir)

    def load_defaults(self) -> UserProfile:
        with self._lock:
            if not self.profile_path.exists():
                return UserProfile()
            return UserProfile.model_validate_json(self.profile_path.read_text(encoding="utf-8"))

    def save_defaults(self, values: Mapping[str, object]) -> UserProfile:
        profile = UserProfile.model_validate({"schema_version": 1, **dict(values)})
        self._atomic_write(self.profile_path, profile.model_dump_json(indent=2) + "\n")
        return profile

    def load_style(self) -> str:
        with self._lock:
            return self.style_path.read_text(encoding="utf-8") if self.style_path.exists() else ""

    def save_style(self, markdown: str) -> None:
        self._atomic_write(self.style_path, markdown)

    def clear(self) -> None:
        with self._lock:
            for path in (self.profile_path, self.style_path):
                if path.exists():
                    path.unlink()

    def _atomic_write(self, path: Path, content: str) -> None:
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            try:
                temporary.write_text(content, encoding="utf-8")
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()


def merge_preferences(
    *,
    defaults: Mapping[str, object],
    profile: Mapping[str, object],
    explicit: Mapping[str, object],
    natural_language: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Merge from lowest to highest priority, ignoring unspecified None values."""
    result: dict[str, object] = {}
    for layer in (defaults, profile, explicit, natural_language or {}):
        result.update({key: value for key, value in layer.items() if value is not None and key != "schema_version"})
    return result
