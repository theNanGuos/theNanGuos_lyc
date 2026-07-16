from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from the_nanguos.knowledge import (
    KnowledgeCatalog,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeStore,
    KnowledgeType,
)
from the_nanguos.knowledge.retriever import KnowledgeRetriever, KeywordKnowledgeRetriever


def document(
    entry_id: str,
    *,
    name: str,
    aliases: list[str],
    tags: list[str] | None = None,
    related_styles: list[str] | None = None,
    body: str = "warm body keyword",
) -> KnowledgeDocument:
    kind = entry_id.split(".", 1)[0]
    frontmatter: dict[str, object] = {
        "id": entry_id,
        "type": kind,
        "name": name,
        "aliases": aliases,
        "tags": tags or ["shared"],
        "related_styles": related_styles or [],
        "sources": ["https://example.com/reference"],
        "updated_at": "2026-07-14",
    }
    if kind == "track":
        frontmatter.update({"artist": "Artist", "year": 1982, "style_refs": ["style.city_pop"]})
    return KnowledgeDocument(
        frontmatter=frontmatter,
        body=body,
        sections={"定义": body, "曲式": "结构层次", "配器": "乐器分工", "抽象经验": "保持原创"},
        source_path=f"{kind}s/{entry_id.split('.', 1)[1]}.md",
    )


def catalog(*documents: KnowledgeDocument) -> KnowledgeCatalog:
    return KnowledgeCatalog(
        indexed_at=datetime(2026, 7, 14, tzinfo=UTC),
        fingerprint="test-catalog",
        documents=list(documents),
    )


def test_keyword_retriever_uses_fixed_explainable_weights() -> None:
    source = catalog(document(
        "style.city_pop",
        name="City Pop",
        aliases=["城市流行", "シティ・ポップ"],
        tags=["urban", "disco"],
        body="warm metropolitan production",
    ))

    context = KeywordKnowledgeRetriever().retrieve(
        KnowledgeQuery(raw_text="CITY　POP、城市流行 urban disco warm"), source
    )

    assert isinstance(KeywordKnowledgeRetriever(), KnowledgeRetriever)
    assert context.entries[0].id == "style.city_pop"
    assert context.entries[0].score == 25  # name 10 + alias 8 + two tags 6 + capped body 1


def test_alias_and_cross_reference_match_chinese_and_structured_terms() -> None:
    source = catalog(
        document("style.city_pop", name="City Pop", aliases=["城市流行"]),
        document(
            "instrument.rhodes",
            name="Rhodes Electric Piano",
            aliases=["罗兹电钢琴"],
            related_styles=["style.city_pop"],
        ),
    )
    retriever = KeywordKnowledgeRetriever()

    alias_hit = retriever.retrieve(KnowledgeQuery(raw_text="想要罗兹电钢琴的温暖质感"), source)
    reference_hit = retriever.retrieve(
        KnowledgeQuery(styles=["style.city_pop"], requested_types=[KnowledgeType.INSTRUMENT]), source
    )

    assert alias_hit.entries[0].id == "instrument.rhodes"
    assert alias_hit.entries[0].score >= 8
    assert [(entry.id, entry.score) for entry in reference_hit.entries] == [("instrument.rhodes", 4)]


def test_retrieval_applies_stable_sort_type_filter_top_k_quotas_and_budget() -> None:
    source = catalog(
        document("style.b", name="B", aliases=["shared"]),
        document("style.a", name="A", aliases=["shared"]),
        document("instrument.x", name="X", aliases=["shared"]),
    )
    retriever = KeywordKnowledgeRetriever()

    context = retriever.retrieve(
        KnowledgeQuery(raw_text="shared"),
        source,
        top_k=2,
        char_budget=200,
        type_quotas={KnowledgeType.STYLE: 1, KnowledgeType.INSTRUMENT: 1},
    )

    assert [entry.id for entry in context.entries] == ["instrument.x", "style.a"]
    assert sum(len(entry.excerpt) for entry in context.entries) <= 200
    assert retriever.retrieve(KnowledgeQuery(), source).entries == []


def test_agent_views_isolate_track_analysis_and_select_different_sections() -> None:
    root = Path(__file__).resolve().parents[1] / "knowledge"
    source = KnowledgeStore(root).load_catalog()
    retriever = KeywordKnowledgeRetriever()
    context = retriever.retrieve(
        KnowledgeQuery(raw_text="City Pop Rhodes Plastic Love"), source, top_k=10, char_budget=4000
    )

    conductor = retriever.view_for("ConductorAgent", context, source)
    lyrics = retriever.view_for("LyricsAgent", context, source)
    planner = retriever.view_for("MusicPlannerAgent", context, source)
    arrangement = retriever.view_for("ArrangementAgent", context, source)

    assert all(entry.type != KnowledgeType.TRACK for entry in conductor.entries)
    assert all(entry.type != KnowledgeType.TRACK for entry in lyrics.entries)
    assert "曲式" in next(entry.excerpt for entry in planner.entries if entry.type == KnowledgeType.TRACK)
    arrangement_track = next(entry.excerpt for entry in arrangement.entries if entry.type == KnowledgeType.TRACK)
    assert "配器" in arrangement_track
    assert "曲式" not in arrangement_track
