from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path

import pytest

from the_nanguos.knowledge import KnowledgeStore, KeywordKnowledgeRetriever
from the_nanguos.services.generation import GenerationService
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.storage import ArtifactStore


class PayloadLLM:
    def __init__(self) -> None:
        self.results = deque([
            {
                "song_spec": {"title": "Night", "language": "zh", "genre": "City Pop", "mood": ["warm"], "duration_seconds": 60, "structure": ["verse"]},
                "task_plan": {"goal": "x", "steps": [{"id": "lyrics", "actor": "LyricsAgent", "task": "write", "output_key": "lyrics_result"}]},
            },
            {"sections": [{"name": "verse", "lines": ["hello"]}]},
            {"bpm": 90, "key": "C major", "sections": [{"name": "verse", "duration_seconds": 60, "chords": ["C"], "melody_intent": "soft"}]},
            {"instruments": ["piano"], "mix_style": "warm", "dynamic_curve": "rise", "suno_style": "warm pop", "sections": [{"name": "verse", "arrangement": "piano"}]},
        ])
        self.payloads: list[dict[str, object]] = []

    async def generate_structured(self, *, messages, response_model):
        self.payloads.append(json.loads(messages[1]["content"]))
        return response_model.model_validate(self.results.popleft())


def project_knowledge() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


def test_collaboration_log_saves_references_not_excerpts_or_markdown(tmp_path: Path) -> None:
    service = GenerationService(
        llm=PayloadLLM(),
        artifact_store=ArtifactStore(tmp_path),
        submit=False,
        knowledge_store=KnowledgeStore(project_knowledge()),
        knowledge_retriever=KeywordKnowledgeRetriever(),
    )
    record = GenerationRecord(request_id="knowledge-log", user_request="City Pop Rhodes Plastic Love")

    asyncio.run(service(record))

    raw = (tmp_path / record.request_id / "collaboration_log.json").read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["knowledge"]["used"] is True
    assert payload["knowledge"]["references"]
    assert set(payload["knowledge"]["references"][0]) == {"id", "type", "score", "source_path"}
    assert "excerpt" not in raw
    assert "City Pop 是一个边界较宽" not in raw
    assert all(not Path(item["source_path"]).is_absolute() for item in payload["knowledge"]["references"])


def test_knowledge_degradation_log_does_not_leak_internal_exception(tmp_path: Path) -> None:
    class BrokenStore:
        def load_catalog(self):
            raise OSError("C:/private/knowledge secret-content")

    service = GenerationService(
        llm=PayloadLLM(),
        artifact_store=ArtifactStore(tmp_path),
        submit=False,
        knowledge_store=BrokenStore(),
        knowledge_retriever=KeywordKnowledgeRetriever(),
    )
    record = GenerationRecord(request_id="knowledge-warning", user_request="warm pop")

    asyncio.run(service(record))

    raw = (tmp_path / record.request_id / "collaboration_log.json").read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["knowledge"]["used"] is False
    assert payload["knowledge"]["warnings"][0]["code"] == "knowledge_unavailable"
    assert "private" not in raw
    assert "secret-content" not in raw


def test_role_prompts_keep_track_analysis_out_of_lyrics(tmp_path: Path) -> None:
    llm = PayloadLLM()
    service = GenerationService(
        llm=llm,
        artifact_store=ArtifactStore(tmp_path),
        submit=False,
        knowledge_store=KnowledgeStore(project_knowledge()),
        knowledge_retriever=KeywordKnowledgeRetriever(),
    )
    record = GenerationRecord(request_id="knowledge-role", user_request="City Pop Rhodes Plastic Love")

    asyncio.run(service(record))
    lyrics_payload = json.dumps(llm.payloads[1], ensure_ascii=False)
    planner_payload = json.dumps(llm.payloads[2], ensure_ascii=False)
    assert "Plastic Love" not in lyrics_payload
    assert "wmg.jp" not in lyrics_payload
    assert "Plastic Love" in planner_payload


def test_store_does_not_follow_a_symlinked_knowledge_directory(tmp_path: Path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    (external / "outside.md").write_text(
        """---
id: style.outside
type: style
name: Outside
aliases: [outside]
tags: [outside]
sources: [https://example.com]
updated_at: 2026-07-14
---
# 定义
outside
""",
        encoding="utf-8",
    )
    root = tmp_path / "knowledge"
    root.mkdir()
    try:
        (root / "styles").symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    catalog = KnowledgeStore(root).load_catalog()

    assert catalog.documents == []
    assert any(warning.code == "unsafe_path" for warning in catalog.warnings)
