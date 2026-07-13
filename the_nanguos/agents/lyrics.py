from the_nanguos.schemas import LyricsResult, SongSpec

from ._base import StructuredAgent


class LyricsAgent(StructuredAgent):
    name = "LyricsAgent"
    purpose = "Write sectioned lyrics only; do not produce API request fields."

    async def run(self, song_spec: SongSpec, *, instruction: str = "") -> LyricsResult:
        return await self._generate(LyricsResult, {"song_spec": song_spec.model_dump(mode="json"), "instruction": instruction})
