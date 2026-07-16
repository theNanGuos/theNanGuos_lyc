from the_nanguos.schemas import LyricsResult, SongSpec
from the_nanguos.knowledge import AgentKnowledgeView

from ._base import StructuredAgent


class LyricsAgent(StructuredAgent):
    name = "LyricsAgent"
    purpose = "Write sectioned lyrics only; do not produce API request fields."

    async def run(self, song_spec: SongSpec, *, instruction: str = "", knowledge: AgentKnowledgeView | None = None) -> LyricsResult:
        payload = {"song_spec": song_spec.model_dump(mode="json"), "instruction": instruction}
        if knowledge is not None:
            payload["knowledge_context"] = knowledge.model_dump(mode="json")
        return await self._generate(LyricsResult, payload)
