from the_nanguos.schemas import ArrangementResult, LyricsResult, MusicPlanResult, SongSpec

from ._base import StructuredAgent


class ArrangementAgent(StructuredAgent):
    name = "ArrangementAgent"
    purpose = "Create instrumentation, production direction and a concise Suno style description."

    async def run(self, song_spec: SongSpec, lyrics: LyricsResult, music_plan: MusicPlanResult, *, instruction: str = "") -> ArrangementResult:
        return await self._generate(
            ArrangementResult,
            {"song_spec": song_spec.model_dump(mode="json"), "lyrics": lyrics.model_dump(mode="json"), "music_plan": music_plan.model_dump(mode="json"), "instruction": instruction},
        )
