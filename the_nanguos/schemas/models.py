from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AgentActor(StrEnum):
    CONDUCTOR = "ConductorAgent"
    LYRICS = "LyricsAgent"
    MUSIC_PLANNER = "MusicPlannerAgent"
    ARRANGEMENT = "ArrangementAgent"


class TaskStep(StrictModel):
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_-]*$")
    actor: AgentActor
    task: str = Field(min_length=1)
    input_keys: list[str] = Field(default_factory=list)
    output_key: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)


class TaskPlan(StrictModel):
    goal: str = Field(min_length=1)
    steps: list[TaskStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_graph(self) -> "TaskPlan":
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("TaskPlan step IDs must be unique")
        known = set(ids)
        for step in self.steps:
            unknown = set(step.depends_on) - known
            if unknown:
                raise ValueError(f"unknown dependencies for {step.id}: {sorted(unknown)}")
        edges = {step.id: step.depends_on for step in self.steps}
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("TaskPlan dependencies must be acyclic")
            if node in visited:
                return
            visiting.add(node)
            for dep in edges[node]:
                visit(dep)
            visiting.remove(node)
            visited.add(node)
        for node in ids:
            visit(node)
        return self


class VocalSpec(StrictModel):
    enabled: bool = True
    gender: Literal["male", "female"] | None = None


class TempoSpec(StrictModel):
    bpm: int = Field(default=90, ge=40, le=240)
    feel: str = "steady"


class SongConstraints(StrictModel):
    explicit: bool = False
    avoid: list[str] = Field(default_factory=list)


class SongSpec(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=2, max_length=16)
    genre: str = Field(min_length=1, max_length=120)
    mood: list[str] = Field(min_length=1)
    duration_seconds: int = Field(ge=30, le=600)
    vocal: VocalSpec = Field(default_factory=VocalSpec)
    tempo: TempoSpec = Field(default_factory=TempoSpec)
    key: str = "C major"
    structure: list[str] = Field(min_length=1)
    constraints: SongConstraints = Field(default_factory=SongConstraints)


class LyricsSection(StrictModel):
    name: str = Field(min_length=1)
    lines: list[str] = Field(default_factory=list)


class LyricsResult(StrictModel):
    sections: list[LyricsSection] = Field(min_length=1)


class MusicSection(StrictModel):
    name: str = Field(min_length=1)
    duration_seconds: int = Field(ge=1, le=600)
    chords: list[str] = Field(default_factory=list)
    melody_intent: str = Field(min_length=1)


class MusicPlanResult(StrictModel):
    bpm: int = Field(ge=40, le=240)
    key: str = Field(min_length=1)
    sections: list[MusicSection] = Field(min_length=1)


class ArrangementSection(StrictModel):
    name: str = Field(min_length=1)
    arrangement: str = Field(min_length=1)


class ArrangementResult(StrictModel):
    instruments: list[str] = Field(min_length=1)
    mix_style: str = Field(min_length=1)
    dynamic_curve: str = Field(min_length=1)
    suno_style: str = Field(min_length=1)
    sections: list[ArrangementSection] = Field(min_length=1)


class ConductorResult(StrictModel):
    song_spec: SongSpec
    task_plan: TaskPlan


class ScoreSection(StrictModel):
    name: str
    duration_seconds: int = Field(ge=1, le=600)
    lyrics: list[str] = Field(default_factory=list)
    chords: list[str] = Field(default_factory=list)
    melody_intent: str
    arrangement: str


class GlobalArrangement(StrictModel):
    instruments: list[str]
    mix_style: str
    dynamic_curve: str
    suno_style: str


class ScorePlan(StrictModel):
    sections: list[ScoreSection] = Field(min_length=1)
    global_arrangement: GlobalArrangement


class SunoModel(StrEnum):
    V4 = "V4"
    V4_5 = "V4_5"
    V4_5PLUS = "V4_5PLUS"
    V4_5ALL = "V4_5ALL"
    V5 = "V5"
    V5_5 = "V5_5"


Weight = Annotated[float, Field(ge=0, le=1)]


class SunoRequest(StrictModel):
    custom_mode: bool = Field(alias="customMode")
    instrumental: bool
    model: SunoModel
    callback_url: AnyHttpUrl = Field(alias="callBackUrl")
    prompt: str | None = None
    style: str | None = None
    title: str | None = None
    negative_tags: str | None = Field(default=None, alias="negativeTags")
    vocal_gender: Literal["m", "f"] | None = Field(default=None, alias="vocalGender")
    style_weight: Weight | None = Field(default=None, alias="styleWeight")
    weirdness_constraint: Weight | None = Field(default=None, alias="weirdnessConstraint")
    audio_weight: Weight | None = Field(default=None, alias="audioWeight")

    @model_validator(mode="after")
    def validate_contract(self) -> "SunoRequest":
        if self.custom_mode:
            if not self.style or not self.title:
                raise ValueError("custom mode requires style and title")
            if not self.instrumental and not self.prompt:
                raise ValueError("custom vocal mode requires prompt")
        else:
            if not self.prompt:
                raise ValueError("non-custom mode requires prompt")
            if any(value is not None for value in (self.style, self.title, self.negative_tags, self.vocal_gender, self.style_weight, self.weirdness_constraint, self.audio_weight)):
                raise ValueError("non-custom mode only accepts prompt as creative content")
        prompt_limit = 500 if not self.custom_mode else (3000 if self.model == SunoModel.V4 else 5000)
        style_limit = 200 if self.model == SunoModel.V4 else 1000
        title_limit = 80 if self.model in (SunoModel.V4, SunoModel.V4_5ALL) else 100
        if self.prompt and len(self.prompt) > prompt_limit:
            raise ValueError(f"prompt exceeds {prompt_limit} characters")
        if self.style and len(self.style) > style_limit:
            raise ValueError(f"style exceeds {style_limit} characters")
        if self.title and len(self.title) > title_limit:
            raise ValueError(f"title exceeds {title_limit} characters")
        return self


class SunoAudio(StrictModel):
    id: str
    audio_url: AnyHttpUrl = Field(alias="audioUrl")
    stream_audio_url: AnyHttpUrl | None = Field(default=None, alias="streamAudioUrl")
    image_url: AnyHttpUrl | None = Field(default=None, alias="imageUrl")
    prompt: str | None = None
    model_name: str | None = Field(default=None, alias="modelName")
    title: str
    tags: str | None = None
    create_time: str | None = Field(default=None, alias="createTime")
    duration: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_https(self) -> "SunoAudio":
        for url in (self.audio_url, self.stream_audio_url, self.image_url):
            if url is not None and url.scheme != "https":
                raise ValueError("Suno media URLs must use HTTPS")
        return self


class SunoTaskDetails(StrictModel):
    task_id: str = Field(alias="taskId")
    status: str
    audio_results: list[SunoAudio] = Field(default_factory=list)
    error: dict[str, object] | None = None

    @model_validator(mode="before")
    @classmethod
    def flatten_response(cls, value: object) -> object:
        if isinstance(value, dict) and "response" in value and "audio_results" not in value:
            copied = dict(value)
            response = copied.pop("response")
            if isinstance(response, dict):
                copied["audio_results"] = response.get("sunoData") or []
            return copied
        return value


class CollaborationStep(StrictModel):
    actor: str
    action: str
    output: str | None = None


class ValidationLog(StrictModel):
    passed: bool = False
    warnings: list[str] = Field(default_factory=list)


class SunoLog(StrictModel):
    submitted: bool = False
    task_id: str | None = None
    status: str | None = None
    audio_results: list[SunoAudio] = Field(default_factory=list)
    error: dict[str, object] | None = None
    poll_interval_seconds: float | None = None
    max_wait_seconds: float | None = None
    attempts: int = 0
    elapsed_seconds: float = 0
    last_status: str | None = None
    local_media: list[dict[str, str]] = Field(default_factory=list)


class CollaborationLog(StrictModel):
    request_id: str
    user_request_summary: str
    artifacts: dict[str, str] = Field(default_factory=dict)
    steps: list[CollaborationStep] = Field(default_factory=list)
    validation: ValidationLog = Field(default_factory=ValidationLog)
    suno: SunoLog = Field(default_factory=SunoLog)


class UserProfile(StrictModel):
    schema_version: Literal[1] = 1
    language: str | None = None
    instrumental: bool | None = None
    vocal_gender: Literal["m", "f"] | None = None
    suno_model: SunoModel | None = None
