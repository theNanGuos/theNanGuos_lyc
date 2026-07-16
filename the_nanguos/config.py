from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


class RuntimeConfigurationError(RuntimeError):
    """A safe, user-actionable runtime configuration failure."""


def load_project_env(start_dir: Path | str | None = None) -> Path | None:
    """Load the nearest project .env without overriding explicit environment values."""
    start = Path(start_dir) if start_dir is not None else Path.cwd()
    resolved = start.resolve()
    directories = (resolved, *resolved.parents)
    for directory in directories:
        env_file = directory / ".env"
        if env_file.is_file():
            load_dotenv(env_file, override=False)
            return env_file
    return None
