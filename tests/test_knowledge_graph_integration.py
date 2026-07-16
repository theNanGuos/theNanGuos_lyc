from __future__ import annotations

import asyncio
import inspect
import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from the_nanguos.agents import ArrangementAgent, ConductorAgent, LyricsAgent, MusicPlannerAgent
from the_nanguos.graphs import GraphState
from the_nanguos.graphs.generate_song import NODE_ORDER
from the_nanguos.knowledge import (
    AgentKnowledgeView,
    KnowledgeCatalog,
    KnowledgeContext,
    KnowledgeQuery,
    KnowledgeRetriever,
)
from the_nanguos.schemas import ArrangementResult, ConductorResult, LyricsResult, MusicPlanResult
from the_nanguos.services.generation import GenerationService
from the_nanguos.services import runtime as runtime_module
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.storage import ArtifactStore
from the_nanguos.tools import build_suno_request


RESULTS = [
    {
        "song_spec": {"title": "Night", "language": "zh", "genre": "pop", "mood": ["warm"], "duration_seconds": 60, "structure": ["verse"]},
        "task_plan": {"goal": "x", "steps": [{"id": "lyrics", "actor": "LyricsAgent", "task": "write", "output_key": "lyrics_result"}]},
    },
    {"sections": [{"name": "verse", "lines": ["hello"]}]},
    {"bpm": 90, "key": "C major", "sections": [{"name": "verse", "duration_seconds": 60, "chords": ["C"], "melody_intent": "soft"}]},
    {"instruments": ["piano"], "mix_style": "warm", "dynamic_curve": "rise", "suno_style": "warm pop", "sections": [{"name": "verse", "arrangement": "piano"}]},
]


class RecordingLLM:
    def __init__(self, events: list[str] | None = None) -> None:
        self.results = deque(RESULTS)
        self.payloads: list[dict[str, object]] = []
        self.events = events

    async def generate_structured(self, *, messages, response_model):
        self.payloads.append(json.loads(messages[1]["content"]))
        if self.events is not None:
            self.events.append(f"llm:{response_model.__name__}")
        return response_model.model_validate(self.results.popleft())


class RecordingStore:
    def __init__(self, events: list[str], catalog: KnowledgeCatalog) -> None:
        self.events = events
        self.catalog = catalog

    def load_catalog(self) -> KnowledgeCatalog:
        self.events.append("catalog")
        return self.catalog


class RecordingRetriever(KnowledgeRetriever):
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.queries: list[KnowledgeQuery] = []

    def retrieve(self, query, catalog, **kwargs):
        self.queries.append(query)
        self.events.append("retrieve:structured" if query.styles else "retrieve:initial")
        return KnowledgeContext(catalog_indexed_at=catalog.indexed_at)

    def view_for(self, agent, context, catalog, **kwargs):
        self.events.append(f"view:{agent}")
        return AgentKnowledgeView(agent=agent)


def empty_catalog() -> KnowledgeCatalog:
    return KnowledgeCatalog(indexed_at=datetime(2026, 7, 14, tzinfo=UTC), fingerprint="integration")


def test_fixed_graph_places_two_retrieval_nodes_around_conductor_and_state_is_ephemeral() -> None:
    assert NODE_ORDER[:5] == (
        "init_run",
        "retrieve_initial_knowledge",
        "conductor",
        "retrieve_knowledge",
        "lyrics",
    )
    first = GraphState(user_request="first")
    second = GraphState(user_request="second")
    assert first.initial_knowledge_context is None
    assert first.knowledge_context is None
    assert first.knowledge_warnings == []
    first.knowledge_warnings.append({"code": "test"})
    assert second.knowledge_warnings == []


def test_agents_serialize_only_the_supplied_role_view_into_payloads() -> None:
    llm = RecordingLLM()

    async def run() -> None:
        conductor = await ConductorAgent(llm).run(
            "warm song", knowledge=AgentKnowledgeView(agent="ConductorAgent")
        )
        lyrics = await LyricsAgent(llm).run(
            conductor.song_spec, knowledge=AgentKnowledgeView(agent="LyricsAgent")
        )
        music = await MusicPlannerAgent(llm).run(
            conductor.song_spec, lyrics, knowledge=AgentKnowledgeView(agent="MusicPlannerAgent")
        )
        await ArrangementAgent(llm).run(
            conductor.song_spec,
            lyrics,
            music,
            knowledge=AgentKnowledgeView(agent="ArrangementAgent"),
        )

    asyncio.run(run())

    assert [payload["knowledge_context"]["agent"] for payload in llm.payloads] == [
        "ConductorAgent",
        "LyricsAgent",
        "MusicPlannerAgent",
        "ArrangementAgent",
    ]


def test_generation_retrieves_before_conductor_then_from_validated_song_spec(tmp_path: Path) -> None:
    events: list[str] = []
    retriever = RecordingRetriever(events)
    service = GenerationService(
        llm=RecordingLLM(events),
        artifact_store=ArtifactStore(tmp_path),
        submit=False,
        knowledge_store=RecordingStore(events, empty_catalog()),
        knowledge_retriever=retriever,
    )

    asyncio.run(service(GenerationRecord(request_id="knowledge-order", user_request="warm pop")))

    assert events[:5] == [
        "catalog",
        "retrieve:initial",
        "view:ConductorAgent",
        "llm:ConductorResult",
        "retrieve:structured",
    ]
    assert retriever.queries[0].raw_text == "warm pop"
    assert retriever.queries[1].styles == ["pop"]
    assert retriever.queries[1].moods == ["warm"]
    assert retriever.queries[1].structure == ["verse"]
    assert "knowledge" not in inspect.signature(build_suno_request).parameters


def test_knowledge_failure_does_not_block_existing_generation(tmp_path: Path) -> None:
    class BrokenStore:
        def load_catalog(self):
            raise OSError("unavailable")

    service = GenerationService(
        llm=RecordingLLM(),
        artifact_store=ArtifactStore(tmp_path),
        submit=False,
        knowledge_store=BrokenStore(),
        knowledge_retriever=RecordingRetriever([]),
    )
    record = GenerationRecord(request_id="knowledge-degraded", user_request="warm pop")

    asyncio.run(service(record))

    assert record.status == "completed"
    assert (tmp_path / record.request_id / "song_spec.json").is_file()


def test_environment_runner_injects_one_store_and_retriever_instance(tmp_path: Path, monkeypatch) -> None:
    store_marker = object()
    retriever_marker = object()
    received: list[dict[str, object]] = []

    monkeypatch.setattr(runtime_module, "KnowledgeStore", lambda path: store_marker, raising=False)
    monkeypatch.setattr(runtime_module, "KeywordKnowledgeRetriever", lambda: retriever_marker, raising=False)
    monkeypatch.setattr(runtime_module, "SunoClient", lambda **kwargs: object())
    monkeypatch.setattr(runtime_module, "DeepSeekLLMClient", lambda **kwargs: object())

    class FakeService:
        def __init__(self, **kwargs):
            received.append(kwargs)

        async def __call__(self, record):
            return None

    monkeypatch.setattr(runtime_module, "GenerationService", FakeService)
    runner = runtime_module.environment_runner(
        outputs_dir=tmp_path / "outputs",
        memory_dir=tmp_path / "memory",
        knowledge_dir=tmp_path / "knowledge",
    )

    asyncio.run(runner(GenerationRecord(request_id="runtime-knowledge", user_request="warm pop")))

    assert received[0]["knowledge_store"] is store_marker
    assert received[0]["knowledge_retriever"] is retriever_marker


def test_environment_previewer_supplies_initial_conductor_knowledge(tmp_path: Path, monkeypatch) -> None:
    received: list[object] = []
    source = empty_catalog()
    context = KnowledgeContext(catalog_indexed_at=source.indexed_at)
    view = AgentKnowledgeView(agent="ConductorAgent")

    class FakeStore:
        def __init__(self, path):
            pass

        def load_catalog(self):
            return source

    class FakeRetriever:
        def retrieve(self, query, catalog):
            assert query.raw_text == "warm city pop"
            return context

        def view_for(self, agent, current, catalog):
            assert agent == "ConductorAgent"
            return view

    class FakeAgent:
        def __init__(self, llm):
            pass

        async def run(self, prompt, **kwargs):
            received.append(kwargs["knowledge"])
            return "preview-result"

    monkeypatch.setattr(runtime_module, "KnowledgeStore", FakeStore, raising=False)
    monkeypatch.setattr(runtime_module, "KeywordKnowledgeRetriever", FakeRetriever, raising=False)
    monkeypatch.setattr(runtime_module, "ConductorAgent", FakeAgent)
    monkeypatch.setattr(runtime_module, "DeepSeekLLMClient", lambda **kwargs: object())
    preview = runtime_module.environment_previewer(
        memory_dir=tmp_path / "memory", knowledge_dir=tmp_path / "knowledge"
    )

    result = asyncio.run(preview("warm city pop", {}))

    assert result == "preview-result"
    assert received == [view]
