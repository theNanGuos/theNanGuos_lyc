from __future__ import annotations

import os
from pathlib import Path

from the_nanguos.llm import DeepSeekLLMClient
from the_nanguos.memory import PreferenceStore

from .generation import GenerationService
from .jobs import GenerationRecord
from .storage import ArtifactStore
from .suno import SunoClient


def environment_runner(*, outputs_dir: Path | str = "outputs", memory_dir: Path | str = "memory"):
    store = ArtifactStore(outputs_dir)
    async def run(record: GenerationRecord) -> None:
        suno = SunoClient(api_key=os.environ.get("SUNO_API_KEY", ""), base_url=os.environ.get("SUNO_BASE_URL", "https://api.sunoapi.org"))
        options = dict(record.options)
        options.setdefault("callback_url", os.environ.get("SUNO_CALLBACK_URL", "https://local.invalid/suno-callback"))
        record.options = options
        llm = None if record.stage == "resume_polling" and record.task_id else DeepSeekLLMClient(api_key=os.environ.get("DEEPSEEK_API_KEY", ""), base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"))
        service = GenerationService(llm=llm, artifact_store=store, preferences=PreferenceStore(memory_dir), suno=suno)
        await service(record)
    return run
