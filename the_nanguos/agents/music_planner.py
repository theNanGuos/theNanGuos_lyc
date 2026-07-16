from the_nanguos.schemas import LyricsResult, MusicPlanResult, SongSpec
from the_nanguos.knowledge import AgentKnowledgeView

from ._base import StructuredAgent


class MusicPlannerAgent(StructuredAgent):
    name = "MusicPlannerAgent"
    purpose = "Plan form, BPM, key, chords, section duration and melody intent without note-level notation."

    async def run(self, song_spec: SongSpec, lyrics: LyricsResult, *, instruction: str = "", knowledge: AgentKnowledgeView | None = None) -> MusicPlanResult:
        payload = {"song_spec": song_spec.model_dump(mode="json"), "lyrics": lyrics.model_dump(mode="json"), "instruction": instruction}
        if knowledge is not None:
            payload["knowledge_context"] = knowledge.model_dump(mode="json")
        return await self._generate(MusicPlanResult, payload)
