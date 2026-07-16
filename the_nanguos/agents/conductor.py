from the_nanguos.schemas import ConductorResult
from the_nanguos.knowledge import AgentKnowledgeView

from ._base import StructuredAgent


class ConductorAgent(StructuredAgent):
    name = "ConductorAgent"
    purpose = "Normalize a music request into SongSpec and a fixed-agent explanatory TaskPlan."

    async def run(self, user_request: str, *, preferences: dict[str, object] | None = None, style_context: str = "", knowledge: AgentKnowledgeView | None = None) -> ConductorResult:
        payload = {"user_request": user_request, "confirmed_preferences": preferences or {}, "style_preferences_markdown": style_context}
        if knowledge is not None:
            payload["knowledge_context"] = knowledge.model_dump(mode="json")
        return await self._generate(
            ConductorResult,
            payload,
        )
