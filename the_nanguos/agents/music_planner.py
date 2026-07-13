from the_nanguos.schemas import LyricsResult, MusicPlanResult, SongSpec

from ._base import StructuredAgent


class MusicPlannerAgent(StructuredAgent):
    name = "MusicPlannerAgent"
    purpose = "Plan form, BPM, key, chords, section duration and melody intent without note-level notation."

    async def run(self, song_spec: SongSpec, lyrics: LyricsResult, *, instruction: str = "") -> MusicPlanResult:
        return await self._generate(MusicPlanResult, {"song_spec": song_spec.model_dump(mode="json"), "lyrics": lyrics.model_dump(mode="json"), "instruction": instruction})
