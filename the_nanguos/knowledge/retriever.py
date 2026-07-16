from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Mapping

from .models import (
    AgentKnowledgeView,
    KnowledgeCatalog,
    KnowledgeContext,
    KnowledgeDocument,
    KnowledgeEntry,
    KnowledgeQuery,
    KnowledgeType,
    TrackKnowledge,
)


BODY_SCORE_CAP = 5
SEPARATOR_PATTERN = re.compile(r"[,，、/|;；:_-]+")
SPACE_PATTERN = re.compile(r"\s+")
LATIN_WORD_PATTERN = re.compile(r"^[a-z0-9. ]+$")

AGENT_SECTION_TERMS: dict[str, dict[KnowledgeType, tuple[str, ...]]] = {
    "ConductorAgent": {
        KnowledgeType.STYLE: ("定义", "听感", "边界", "definition", "character", "boundary"),
        KnowledgeType.INSTRUMENT: ("音色", "角色", "边界", "timbre", "role", "boundary"),
    },
    "LyricsAgent": {
        KnowledgeType.STYLE: ("听感", "情绪", "主题", "语言", "叙事", "mood", "theme", "language", "narrative"),
        KnowledgeType.INSTRUMENT: ("情绪", "角色", "mood", "role"),
    },
    "MusicPlannerAgent": {
        KnowledgeType.STYLE: ("定义", "听感", "节奏", "和声", "曲式", "definition", "rhythm", "harmony", "form"),
        KnowledgeType.TRACK: ("风格判断", "曲式", "抽象经验", "style", "form", "abstract"),
    },
    "ArrangementAgent": {
        KnowledgeType.STYLE: ("制作边界", "常见乐器", "production", "instrument"),
        KnowledgeType.INSTRUMENT: ("音色", "角色", "演奏", "编配", "搭配", "录音", "制作", "timbre", "role", "technique", "arrangement", "production"),
        KnowledgeType.TRACK: ("配器", "制作分析", "抽象经验", "arrangement", "production", "abstract"),
    },
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = SEPARATOR_PATTERN.sub(" ", normalized)
    return SPACE_PATTERN.sub(" ", normalized).strip()


def _contains(haystack: str, term: str) -> bool:
    normalized = _normalize(term)
    if not normalized:
        return False
    if LATIN_WORD_PATTERN.fullmatch(normalized):
        return re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", haystack) is not None
    return normalized in haystack


class KnowledgeRetriever(ABC):
    @abstractmethod
    def retrieve(
        self,
        query: KnowledgeQuery,
        catalog: KnowledgeCatalog,
        *,
        top_k: int = 8,
        char_budget: int = 4_000,
        type_quotas: Mapping[KnowledgeType, int] | None = None,
    ) -> KnowledgeContext:
        raise NotImplementedError

    @abstractmethod
    def view_for(
        self,
        agent: str,
        context: KnowledgeContext,
        catalog: KnowledgeCatalog,
        *,
        char_budget: int = 2_000,
    ) -> AgentKnowledgeView:
        raise NotImplementedError


class KeywordKnowledgeRetriever(KnowledgeRetriever):
    def retrieve(
        self,
        query: KnowledgeQuery,
        catalog: KnowledgeCatalog,
        *,
        top_k: int = 8,
        char_budget: int = 4_000,
        type_quotas: Mapping[KnowledgeType, int] | None = None,
    ) -> KnowledgeContext:
        query_values = [
            query.raw_text,
            *query.styles,
            *query.moods,
            *query.structure,
            query.vocal or "",
            *query.instruments,
        ]
        haystack = _normalize(" ".join(value for value in query_values if value))
        if not haystack or top_k <= 0 or char_budget <= 0:
            return KnowledgeContext(catalog_indexed_at=catalog.indexed_at, warnings=catalog.warnings)
        requested = set(query.requested_types)
        body_terms = {term for term in haystack.split() if len(term) >= 2}
        scored: list[tuple[float, KnowledgeDocument]] = []
        for document in catalog.documents:
            if requested and document.frontmatter.type not in requested:
                continue
            score = self._score(document, haystack, body_terms)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1].frontmatter.id))

        entries: list[KnowledgeEntry] = []
        counts: dict[KnowledgeType, int] = {}
        remaining = char_budget
        for score, document in scored:
            kind = document.frontmatter.type
            quota = type_quotas.get(kind) if type_quotas is not None else None
            if quota is not None and counts.get(kind, 0) >= max(0, quota):
                continue
            excerpt = self._document_excerpt(document)
            if not excerpt or remaining <= 0:
                continue
            excerpt = excerpt[:remaining]
            entries.append(
                KnowledgeEntry(
                    id=document.frontmatter.id,
                    type=kind,
                    score=score,
                    excerpt=excerpt,
                    source_path=document.source_path,
                )
            )
            remaining -= len(excerpt)
            counts[kind] = counts.get(kind, 0) + 1
            if len(entries) >= top_k:
                break
        return KnowledgeContext(catalog_indexed_at=catalog.indexed_at, entries=entries, warnings=catalog.warnings)

    def view_for(
        self,
        agent: str,
        context: KnowledgeContext,
        catalog: KnowledgeCatalog,
        *,
        char_budget: int = 2_000,
    ) -> AgentKnowledgeView:
        if agent not in AGENT_SECTION_TERMS:
            raise ValueError(f"unsupported agent knowledge view: {agent}")
        documents = {document.frontmatter.id: document for document in catalog.documents}
        entries: list[KnowledgeEntry] = []
        remaining = max(0, char_budget)
        for source_entry in context.entries:
            document = documents.get(source_entry.id)
            if document is None:
                continue
            terms = AGENT_SECTION_TERMS[agent].get(document.frontmatter.type)
            if not terms:
                continue
            excerpt = self._section_excerpt(document, terms)
            if not excerpt or remaining <= 0:
                continue
            excerpt = excerpt[:remaining]
            entries.append(source_entry.model_copy(update={"excerpt": excerpt}))
            remaining -= len(excerpt)
        return AgentKnowledgeView(agent=agent, entries=entries, warnings=context.warnings)

    @staticmethod
    def _score(document: KnowledgeDocument, haystack: str, body_terms: set[str]) -> float:
        metadata = document.frontmatter
        score = 0
        if _contains(haystack, metadata.id) or _contains(haystack, metadata.name):
            score += 10
        if any(_contains(haystack, alias) for alias in metadata.aliases):
            score += 8
        references = [*metadata.related_styles, *metadata.related_instruments, *metadata.reference_tracks]
        if isinstance(metadata, TrackKnowledge):
            references.extend(metadata.style_refs)
        if any(_contains(haystack, reference) for reference in references):
            score += 4
        score += 3 * sum(1 for tag in metadata.tags if _contains(haystack, tag))
        body = _normalize(document.body)
        score += min(BODY_SCORE_CAP, sum(1 for term in body_terms if _contains(body, term)))
        return float(score)

    @staticmethod
    def _document_excerpt(document: KnowledgeDocument) -> str:
        if not document.sections:
            return document.body
        return "\n\n".join(f"## {heading}\n{content}" for heading, content in document.sections.items() if content)

    @staticmethod
    def _section_excerpt(document: KnowledgeDocument, terms: tuple[str, ...]) -> str:
        selected = []
        for heading, content in document.sections.items():
            normalized_heading = _normalize(heading)
            if content and any(_normalize(term) in normalized_heading for term in terms):
                selected.append(f"## {heading}\n{content}")
        return "\n\n".join(selected)
