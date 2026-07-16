import pytest
from pydantic import ValidationError

from the_nanguos.schemas import SongSpec, SunoAudio, SunoRequest, TaskPlan


def test_task_plan_rejects_unknown_actor_duplicate_and_cycles() -> None:
    base = {"goal": "song", "steps": [{"id": "a", "actor": "LyricsAgent", "task": "write", "output_key": "lyrics_result"}]}
    assert TaskPlan.model_validate(base).steps[0].id == "a"
    for steps in (
        [{**base["steps"][0], "actor": "Unknown"}],
        [base["steps"][0], base["steps"][0]],
        [{**base["steps"][0], "depends_on": ["missing"]}],
        [base["steps"][0], {"id": "b", "actor": "ArrangementAgent", "task": "arrange", "output_key": "arrangement_result", "depends_on": ["b"]}],
    ):
        with pytest.raises(ValidationError):
            TaskPlan(goal="song", steps=steps)


def test_suno_request_validates_mode_limits_and_weights() -> None:
    valid = SunoRequest(customMode=True, instrumental=False, model="V5", callBackUrl="https://example.com/callback", prompt="lyrics", style="pop", title="Title")
    assert valid.model == "V5"
    with pytest.raises(ValidationError):
        SunoRequest(customMode=True, instrumental=False, model="V5", callBackUrl="https://example.com/callback", prompt="", style="pop", title="Title")
    with pytest.raises(ValidationError):
        SunoRequest(customMode=False, instrumental=False, model="V5", callBackUrl="https://example.com/callback", prompt="x", style="must be empty")
    with pytest.raises(ValidationError):
        SunoRequest(customMode=True, instrumental=True, model="V4", callBackUrl="https://example.com/callback", style="x" * 201, title="Title", styleWeight=1.1)


def test_kie_limits_titles_to_80_characters_for_every_model() -> None:
    for model in ("V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5", "V5_5"):
        with pytest.raises(ValidationError):
            SunoRequest(
                customMode=True,
                instrumental=True,
                model=model,
                callBackUrl="https://callback.invalid/kie/suno",
                style="ambient",
                title="x" * 81,
            )


def test_song_spec_and_audio_validate_boundaries() -> None:
    spec = SongSpec(title="Night", language="zh", genre="lo-fi", mood=["warm"], duration_seconds=90, structure=["intro", "verse"])
    assert spec.vocal.enabled is True
    with pytest.raises(ValidationError):
        SunoAudio(id="a", audio_url="http://unsafe.test/a.mp3", title="x")
