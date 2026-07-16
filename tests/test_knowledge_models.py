from __future__ import annotations

from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

from the_nanguos.knowledge.models import (
    AgentKnowledgeView,
    KnowledgeContext,
    KnowledgeDocument,
    KnowledgeEntry,
    KnowledgeFrontmatter,
    KnowledgeQuery,
    KnowledgeReference,
    KnowledgeType,
)


def frontmatter(kind: str) -> dict[str, object]:
    base: dict[str, object] = {
        "id": f"{kind}.example",
        "type": kind,
        "name": f"Example {kind}",
        "aliases": [f"示例{kind}"],
        "tags": ["warm"],
        "sources": ["https://example.com/reference"],
        "updated_at": "2026-07-14",
    }
    if kind == "track":
        base.update({"artist": "Example Artist", "year": 1982, "style_refs": ["style.example"]})
    return base


@pytest.mark.parametrize("kind", ["style", "instrument", "track"])
def test_frontmatter_accepts_all_three_knowledge_types(kind: str) -> None:
    model = TypeAdapter(KnowledgeFrontmatter).validate_python(frontmatter(kind))

    assert model.type == KnowledgeType(kind)
    assert model.updated_at == date(2026, 7, 14)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "Example Without Prefix"),
        ("type", "genre"),
        ("updated_at", "2026/07/14"),
        ("sources", ["file:///secret.md"]),
        ("aliases", [""]),
        ("aliases", ["same", "Same"]),
    ],
)
def test_frontmatter_rejects_invalid_common_fields(field: str, value: object) -> None:
    payload = frontmatter("style")
    payload[field] = value

    with pytest.raises(ValidationError):
        TypeAdapter(KnowledgeFrontmatter).validate_python(payload)


def test_frontmatter_requires_declared_common_fields() -> None:
    payload = frontmatter("instrument")
    payload.pop("sources")

    with pytest.raises(ValidationError):
        TypeAdapter(KnowledgeFrontmatter).validate_python(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("artist", ""), ("year", 999), ("year", 3000), ("style_refs", [])],
)
def test_track_frontmatter_enforces_analysis_metadata_boundaries(field: str, value: object) -> None:
    payload = frontmatter("track")
    payload[field] = value

    with pytest.raises(ValidationError):
        TypeAdapter(KnowledgeFrontmatter).validate_python(payload)


def test_context_and_agent_view_keep_excerpt_separate_from_log_reference() -> None:
    document = KnowledgeDocument(
        frontmatter=frontmatter("style"),
        body="# 定义\n温暖、克制的流行风格。",
        sections={"定义": "温暖、克制的流行风格。"},
        source_path="styles/example.md",
    )
    entry = KnowledgeEntry(
        id=document.frontmatter.id,
        type=document.frontmatter.type,
        score=10,
        excerpt="温暖、克制的流行风格。",
        source_path=document.source_path,
    )
    context = KnowledgeContext(catalog_indexed_at="2026-07-14T10:00:00Z", entries=[entry])
    query = KnowledgeQuery(raw_text="温暖的 example 风格", requested_types=[KnowledgeType.STYLE])
    view = AgentKnowledgeView(agent="ConductorAgent", entries=context.entries)
    reference = KnowledgeReference.model_validate(entry.model_dump(exclude={"excerpt"}))

    assert query.raw_text.startswith("温暖")
    assert view.entries[0].excerpt
    assert "excerpt" not in reference.model_dump()
