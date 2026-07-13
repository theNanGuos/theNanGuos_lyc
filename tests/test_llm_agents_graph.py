import asyncio
from collections import deque

import httpx
import pytest

from the_nanguos.agents import ArrangementAgent, ConductorAgent, LyricsAgent, MusicPlannerAgent
from the_nanguos.graphs import GraphState, build_generate_song_graph
from the_nanguos.llm import DeepSeekLLMClient, StructuredGenerationError
from the_nanguos.schemas import ArrangementResult, LyricsResult, MusicPlanResult, SongSpec, TaskPlan


class FakeLLM:
    def __init__(self, results): self.results = deque(results)
    async def generate_structured(self, *, messages, response_model):
        return response_model.model_validate(self.results.popleft())


def test_four_agents_use_structured_contracts() -> None:
    plan = {"goal": "make song", "steps": [{"id": "lyrics", "actor": "LyricsAgent", "task": "write", "output_key": "lyrics_result"}]}
    spec = {"title": "Night", "language": "zh", "genre": "lo-fi", "mood": ["warm"], "duration_seconds": 90, "structure": ["verse"]}
    llm = FakeLLM([{"song_spec": spec, "task_plan": plan}, {"sections": [{"name": "verse", "lines": ["夜色"]}]}, {"bpm": 78, "key": "C major", "sections": [{"name": "verse", "duration_seconds": 90, "chords": ["Cmaj7"], "melody_intent": "gentle"}]}, {"instruments": ["piano"], "mix_style": "warm", "dynamic_curve": "soft", "suno_style": "warm lo-fi", "sections": [{"name": "verse", "arrangement": "piano"}]}])
    async def run():
        c = await ConductorAgent(llm).run("warm song")
        l = await LyricsAgent(llm).run(c.song_spec)
        m = await MusicPlannerAgent(llm).run(c.song_spec, l)
        a = await ArrangementAgent(llm).run(c.song_spec, l, m)
        return c, l, m, a
    c, l, m, a = asyncio.run(run())
    assert isinstance(c.song_spec, SongSpec) and isinstance(c.task_plan, TaskPlan)
    assert isinstance(l, LyricsResult) and isinstance(m, MusicPlanResult) and isinstance(a, ArrangementResult)


def test_deepseek_retries_empty_and_discards_reasoning() -> None:
    responses = deque([
        {"choices": [{"message": {"content": "", "reasoning_content": "secret"}}]},
        {"choices": [{"message": {"content": '{"title":"Night","language":"zh","genre":"pop","mood":["warm"],"duration_seconds":90,"structure":["verse"]}', "reasoning_content": "never expose"}}]},
    ])
    async def handler(request): return httpx.Response(200, json=responses.popleft())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = DeepSeekLLMClient(api_key="secret", http_client=http, max_retries=2)
            return await client.generate_structured(messages=[{"role": "user", "content": "x"}], response_model=SongSpec)
    result = asyncio.run(run())
    assert result.title == "Night"


def test_deepseek_fails_after_retries() -> None:
    async def handler(request): return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            await DeepSeekLLMClient(api_key="secret", http_client=http, max_retries=2).generate_structured(messages=[{"role": "user", "content": "x"}], response_model=SongSpec)
    with pytest.raises(StructuredGenerationError): asyncio.run(run())


def test_graph_is_fixed_and_has_no_checkpointer() -> None:
    graph = build_generate_song_graph()
    assert graph.checkpointer is None
    state = GraphState(user_request="x")
    assert state.errors == []
