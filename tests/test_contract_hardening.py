import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from the_nanguos.graphs.generate_song import build_generate_song_graph, find_step
from the_nanguos.graphs.generate_song import NODE_ORDER, REMOTE_NODE_ORDER
from the_nanguos.graphs.state import GraphState
from the_nanguos.memory import PreferenceStore
from the_nanguos.schemas import SunoAudio, SunoRequest, SunoTaskDetails, TaskPlan


def test_suno_official_camel_case_maps_to_internal_models() -> None:
    audio = SunoAudio.model_validate({"id": "a", "audioUrl": "https://x/a.mp3", "streamAudioUrl": "https://x/s", "imageUrl": "https://x/i.jpg", "modelName": "v5", "createTime": "now", "title": "T"})
    assert str(audio.audio_url) == "https://x/a.mp3" and audio.model_name == "v5"
    details = SunoTaskDetails.model_validate({"taskId": "t", "status": "SUCCESS", "response": {"sunoData": [audio.model_dump(mode="json", by_alias=True)]}})
    assert details.audio_results[0].id == "a"


def test_non_custom_request_rejects_weights() -> None:
    with pytest.raises(ValidationError):
        SunoRequest.model_validate({"customMode": False, "instrumental": True, "model": "V5", "callBackUrl": "https://x/c", "prompt": "x", "audioWeight": .5})


def test_missing_graph_nodes_fail_loudly_and_find_step_uses_id() -> None:
    plan = TaskPlan.model_validate({"goal": "x", "steps": [{"id": "lyrics", "actor": "LyricsAgent", "task": "x", "output_key": "x"}]})
    assert find_step(plan, "lyrics") is not None
    with pytest.raises(RuntimeError, match="not configured"):
        build_generate_song_graph().invoke({"user_request": "x"})


def test_preference_store_instances_share_path_lock(tmp_path: Path) -> None:
    left = PreferenceStore(tmp_path)
    right = PreferenceStore(tmp_path)
    assert left._lock is right._lock


def test_graph_node_order_and_submission_branch() -> None:
    async def run(submit: bool):
        seen = []
        def node(name):
            async def execute(state): seen.append(name); return {}
            return execute
        graph = build_generate_song_graph(nodes={name: node(name) for name in NODE_ORDER + REMOTE_NODE_ORDER})
        await graph.ainvoke(GraphState(user_request="x", submit=submit))
        return seen
    assert asyncio.run(run(False)) == list(NODE_ORDER)
    assert asyncio.run(run(True)) == list(NODE_ORDER + REMOTE_NODE_ORDER)


def test_graph_poll_failure_does_not_enter_save_media() -> None:
    seen = []
    def node(name):
        async def execute(state):
            seen.append(name)
            if name == "poll_suno": raise RuntimeError("poll failed")
            return {}
        return execute
    graph = build_generate_song_graph(nodes={name: node(name) for name in NODE_ORDER + REMOTE_NODE_ORDER})
    with pytest.raises(RuntimeError, match="poll failed"):
        asyncio.run(graph.ainvoke(GraphState(user_request="x", submit=True)))
    assert "poll_suno" in seen and "save_media" not in seen
