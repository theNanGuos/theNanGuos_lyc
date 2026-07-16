from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


KNOWLEDGE_ID_PATTERN = r"^(style|instrument|track)\.[a-z0-9]+(?:[._-][a-z0-9]+)*$"


def _relative_source_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or PureWindowsPath(value).is_absolute() or ".." in path.parts:
        raise ValueError("source_path must be a safe relative path")
    return normalized


class KnowledgeType(StrEnum):
    STYLE = "style"
    INSTRUMENT = "instrument"
    TRACK = "track"


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeBaseFields(KnowledgeModel):
    id: str = Field(pattern=KNOWLEDGE_ID_PATTERN)
    name: str = Field(min_length=1, max_length=160)
    aliases: list[str] = Field(min_length=1)
    tags: list[str] = Field(min_length=1)
    related_styles: list[str] = Field(default_factory=list)
    related_instruments: list[str] = Field(default_factory=list)
    reference_tracks: list[str] = Field(default_factory=list)
    sources: list[AnyHttpUrl] = Field(min_length=1)
    updated_at: date

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("aliases", "tags")
    @classmethod
    def validate_terms(cls, values: list[str]) -> list[str]:
        stripped = [value.strip() for value in values]
        if any(not value for value in stripped):
            raise ValueError("terms must not be blank")
        folded = [value.casefold() for value in stripped]
        if len(folded) != len(set(folded)):
            raise ValueError("terms must be unique")
        return stripped

    @field_validator("related_styles", "related_instruments", "reference_tracks")
    @classmethod
    def validate_references(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("references must be unique")
        return values

    @model_validator(mode="after")
    def id_prefix_matches_type(self) -> "KnowledgeBaseFields":
        if not self.id.startswith(f"{self.type}."):
            raise ValueError("knowledge id prefix must match type")
        return self


class StyleKnowledge(KnowledgeBaseFields):
    type: Literal[KnowledgeType.STYLE]


class InstrumentKnowledge(KnowledgeBaseFields):
    type: Literal[KnowledgeType.INSTRUMENT]


class TrackKnowledge(KnowledgeBaseFields):
    type: Literal[KnowledgeType.TRACK]
    artist: str = Field(min_length=1, max_length=200)
    year: int = Field(ge=1000, le=datetime.now().year)
    style_refs: list[str] = Field(min_length=1)

    @field_validator("artist")
    @classmethod
    def strip_artist(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artist must not be blank")
        return stripped


KnowledgeFrontmatter = Annotated[
    StyleKnowledge | InstrumentKnowledge | TrackKnowledge,
    Field(discriminator="type"),
]


class KnowledgeWarning(KnowledgeModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    source_path: str | None = None

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str | None) -> str | None:
        return _relative_source_path(value) if value is not None else None


class KnowledgeDocument(KnowledgeModel):
    frontmatter: KnowledgeFrontmatter
    body: str = Field(min_length=1)
    sections: dict[str, str] = Field(default_factory=dict)
    source_path: str = Field(min_length=1)

    _validate_source_path = field_validator("source_path")(_relative_source_path)


class KnowledgeCatalog(KnowledgeModel):
    schema_version: Literal[1] = 1
    indexed_at: datetime
    fingerprint: str = Field(min_length=1)
    documents: list[KnowledgeDocument] = Field(default_factory=list)
    warnings: list[KnowledgeWarning] = Field(default_factory=list)


class KnowledgeQuery(KnowledgeModel):
    raw_text: str = ""
    styles: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    structure: list[str] = Field(default_factory=list)
    vocal: str | None = None
    instruments: list[str] = Field(default_factory=list)
    requested_types: list[KnowledgeType] = Field(default_factory=list)


class KnowledgeEntry(KnowledgeModel):
    id: str = Field(pattern=KNOWLEDGE_ID_PATTERN)
    type: KnowledgeType
    score: float = Field(ge=0)
    excerpt: str
    source_path: str = Field(min_length=1)

    _validate_source_path = field_validator("source_path")(_relative_source_path)


class KnowledgeContext(KnowledgeModel):
    catalog_indexed_at: datetime | None = None
    entries: list[KnowledgeEntry] = Field(default_factory=list)
    warnings: list[KnowledgeWarning] = Field(default_factory=list)


class KnowledgeReference(KnowledgeModel):
    id: str = Field(pattern=KNOWLEDGE_ID_PATTERN)
    type: KnowledgeType
    score: float = Field(ge=0)
    source_path: str = Field(min_length=1)

    _validate_source_path = field_validator("source_path")(_relative_source_path)


class AgentKnowledgeView(KnowledgeModel):
    agent: Literal["ConductorAgent", "LyricsAgent", "MusicPlannerAgent", "ArrangementAgent"]
    entries: list[KnowledgeEntry] = Field(default_factory=list)
    warnings: list[KnowledgeWarning] = Field(default_factory=list)
