from the_nanguos.schemas import ArrangementResult, LyricsResult, MusicPlanResult, SongSpec
from the_nanguos.knowledge import AgentKnowledgeView

from ._base import StructuredAgent


class ArrangementAgent(StructuredAgent):
    name = "ArrangementAgent"
    purpose = "Create instrumentation, production direction and a concise Suno style description."

    async def run(self, song_spec: SongSpec, lyrics: LyricsResult, music_plan: MusicPlanResult, *, instruction: str = "", knowledge: AgentKnowledgeView | None = None) -> ArrangementResult:
        payload = {"song_spec": song_spec.model_dump(mode="json"), "lyrics": lyrics.model_dump(mode="json"), "music_plan": music_plan.model_dump(mode="json"), "instruction": instruction}
        if knowledge is not None:
            payload["knowledge_context"] = knowledge.model_dump(mode="json")
        return await self._generate(
            ArrangementResult,
            payload,
        )
