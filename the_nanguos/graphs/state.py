from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from the_nanguos.schemas import (
    ArrangementResult,
    CollaborationLog,
    LyricsResult,
    MusicPlanResult,
    ScorePlan,
    SongSpec,
    SunoRequest,
    TaskPlan,
)


class GraphState(BaseModel):
    """Ephemeral state for one invocation; never attached to a checkpointer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    request_id: str | None = None
    user_request: str
    submit: bool = True
    resume_polling: bool = False
    output_dir: Path | None = None
    task_plan: TaskPlan | None = None
    song_spec: SongSpec | None = None
    lyrics_result: LyricsResult | None = None
    music_plan_result: MusicPlanResult | None = None
    arrangement_result: ArrangementResult | None = None
    score_plan: ScorePlan | None = None
    suno_request: SunoRequest | None = None
    validation_result: dict[str, Any] | None = None
    suno_task_id: str | None = None
    suno_result: dict[str, Any] | None = None
    polling_stopped: bool = False
    errors: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_log: CollaborationLog | None = None
