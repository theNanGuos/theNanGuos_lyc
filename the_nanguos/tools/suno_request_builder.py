from __future__ import annotations

from the_nanguos.schemas import ArrangementResult, LyricsResult, SongSpec, SunoRequest


def build_suno_request(*, song_spec: SongSpec, lyrics: LyricsResult, arrangement: ArrangementResult, callback_url: str, model: str = "V5", instrumental: bool | None = None, custom_mode: bool = True, negative_tags: str | None = None, vocal_gender: str | None = None, style_weight: float | None = None, weirdness_constraint: float | None = None, audio_weight: float | None = None) -> SunoRequest:
    is_instrumental = not song_spec.vocal.enabled if instrumental is None else instrumental
    lyric_text = "\n\n".join(f"[{section.name}]\n" + "\n".join(section.lines) for section in lyrics.sections)
    if not custom_mode:
        prompt = f"{arrangement.suno_style}. {song_spec.genre}; {', '.join(song_spec.mood)}"
        return SunoRequest.model_validate({"customMode": False, "instrumental": is_instrumental, "model": model, "callBackUrl": callback_url, "prompt": prompt})
    return SunoRequest.model_validate({
        "customMode": True, "instrumental": is_instrumental, "model": model,
        "callBackUrl": callback_url, "prompt": None if is_instrumental else lyric_text,
        "style": arrangement.suno_style, "title": song_spec.title,
        "negativeTags": negative_tags, "vocalGender": vocal_gender,
        "styleWeight": style_weight, "weirdnessConstraint": weirdness_constraint, "audioWeight": audio_weight,
    })
