from __future__ import annotations

import os
import subprocess
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

from the_nanguos import cli
from the_nanguos.api.app import create_app
from the_nanguos.services.runtime import environment_previewer


ROOT = Path(__file__).resolve().parents[1]


def _import_api_from(directory: Path, *, process_value: str | None = None) -> str:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    if process_value is None:
        environment.pop("DEEPSEEK_API_KEY", None)
    else:
        environment["DEEPSEEK_API_KEY"] = process_value
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import the_nanguos.api.app; print(os.environ.get('DEEPSEEK_API_KEY', ''))",
        ],
        cwd=directory,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_api_import_loads_env_file_found_in_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "working-directory"
    nested.mkdir(parents=True)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=from-dotenv\n", encoding="utf-8")

    assert _import_api_from(nested) == "from-dotenv"


def test_explicit_process_environment_overrides_env_file(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=from-dotenv\n", encoding="utf-8")

    assert _import_api_from(nested, process_value="from-process") == "from-process"


def test_cli_loads_project_env_before_starting_api(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli, "load_project_env", lambda: calls.append("loaded"), raising=False)
    monkeypatch.setattr(sys, "argv", ["the-nanguos", "--api"])
    monkeypatch.setitem(
        sys.modules,
        "uvicorn",
        types.SimpleNamespace(run=lambda *args, **kwargs: calls.append("started")),
    )

    cli.main()

    assert calls == ["loaded", "started"]


def test_preview_reports_safe_configuration_error_when_deepseek_key_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    previewer = environment_previewer(
        memory_dir=tmp_path / "memory",
        knowledge_dir=tmp_path / "knowledge",
    )

    with TestClient(
        create_app(
            outputs_dir=tmp_path / "outputs",
            memory_dir=tmp_path / "memory",
            previewer=previewer,
        )
    ) as client:
        response = client.post("/api/generation-previews", json={"prompt": "warm jazz"})

    assert response.status_code == 503
    assert response.json() == {"detail": "DeepSeek service is not configured"}
