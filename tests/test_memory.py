import json

from the_nanguos.memory import PreferenceStore, merge_preferences


def test_preferences_are_explicit_atomic_and_clear_does_not_touch_outputs(tmp_path) -> None:
    output = tmp_path / "outputs" / "keep.txt"
    output.parent.mkdir()
    output.write_text("keep", encoding="utf-8")
    store = PreferenceStore(tmp_path / "memory")
    saved = store.save_defaults({"language": "zh", "instrumental": False, "vocal_gender": "f", "suno_model": "V5"})
    assert saved.language == "zh"
    assert json.loads((tmp_path / "memory" / "user_profile.json").read_text(encoding="utf-8"))["schema_version"] == 1
    store.save_style("## Style\nWarm lo-fi")
    assert store.load_style().startswith("## Style")
    store.clear()
    assert output.read_text(encoding="utf-8") == "keep"


def test_merge_priority_explicit_over_profile_over_defaults() -> None:
    merged = merge_preferences(
        defaults={"language": "en", "suno_model": "V4"},
        profile={"language": "zh", "suno_model": "V5", "vocal_gender": "f"},
        explicit={"language": "ja", "instrumental": True},
        natural_language={"suno_model": "V5_5"},
    )
    assert merged == {"language": "ja", "suno_model": "V5_5", "vocal_gender": "f", "instrumental": True}
