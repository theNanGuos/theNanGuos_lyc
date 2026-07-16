from __future__ import annotations

import os
import logging
from pathlib import Path

from the_nanguos.agents import ConductorAgent
from the_nanguos.config import RuntimeConfigurationError
from the_nanguos.llm import DeepSeekLLMClient
from the_nanguos.knowledge import KnowledgeQuery, KnowledgeStore, KeywordKnowledgeRetriever
from the_nanguos.memory import PreferenceStore, merge_preferences

from .generation import GenerationService
from .jobs import GenerationRecord
from .storage import ArtifactStore
from .suno import SunoClient


logger = logging.getLogger(__name__)


def suno_environment() -> dict[str, str]:
    """Resolve Kie configuration while retaining legacy SUNO_* compatibility."""
    return {
        "api_key": os.environ.get("KIE_API_KEY") or os.environ.get("SUNO_API_KEY", ""),
        "base_url": os.environ.get("KIE_BASE_URL")
        or os.environ.get("SUNO_BASE_URL", "https://api.kie.ai"),
        "callback_url": os.environ.get("KIE_CALLBACK_URL")
        or os.environ.get("SUNO_CALLBACK_URL", "https://callback.invalid/kie/suno"),
    }


def environment_previewer(*, memory_dir: Path | str = "memory", knowledge_dir: Path | str = "knowledge"):
    preferences = PreferenceStore(memory_dir)
    knowledge_store = KnowledgeStore(knowledge_dir)
    knowledge_retriever = KeywordKnowledgeRetriever()

    async def preview(prompt: str, overrides: dict[str, object]):
        profile = preferences.load_defaults().model_dump(mode="json")
        merged = merge_preferences(
            defaults={"language": "zh", "instrumental": False, "suno_model": "V5"},
            profile=profile,
            explicit=overrides,
        )
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeConfigurationError("DeepSeek service is not configured")
        llm = DeepSeekLLMClient(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        )
        knowledge = None
        try:
            catalog = knowledge_store.load_catalog()
            context = knowledge_retriever.retrieve(KnowledgeQuery(raw_text=prompt), catalog)
            knowledge = knowledge_retriever.view_for("ConductorAgent", context, catalog)
        except Exception:
            logger.warning("knowledge preview context is unavailable")
        return await ConductorAgent(llm).run(
            prompt,
            preferences=merged,
            style_context=preferences.load_style(),
            knowledge=knowledge,
        )

    return preview


def environment_runner(*, outputs_dir: Path | str = "outputs", memory_dir: Path | str = "memory", knowledge_dir: Path | str = "knowledge"):
    store = ArtifactStore(outputs_dir)
    knowledge_store = KnowledgeStore(knowledge_dir)
    knowledge_retriever = KeywordKnowledgeRetriever()
    async def run(record: GenerationRecord) -> None:
        provider = suno_environment()
        suno = SunoClient(api_key=provider["api_key"], base_url=provider["base_url"])
        options = dict(record.options)
        options.setdefault("callback_url", provider["callback_url"])
        record.options = options
        llm = None if record.stage == "resume_polling" and record.task_id else DeepSeekLLMClient(api_key=os.environ.get("DEEPSEEK_API_KEY", ""), base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"))
        service = GenerationService(llm=llm, artifact_store=store, preferences=PreferenceStore(memory_dir), suno=suno, knowledge_store=knowledge_store, knowledge_retriever=knowledge_retriever)
        await service(record)
    return run
