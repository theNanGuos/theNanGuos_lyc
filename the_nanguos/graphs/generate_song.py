from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from the_nanguos.schemas import TaskPlan, TaskStep

from .state import GraphState


NODE_ORDER = (
    "init_run",
    "conductor",
    "lyrics",
    "music_planner",
    "arrangement",
    "build_score_plan",
    "validate",
    "build_suno_request",
)
REMOTE_NODE_ORDER = ("submit_suno", "poll_suno", "save_media")


def find_step(plan: TaskPlan, step_id: str) -> TaskStep | None:
    return next((step for step in plan.steps if step.id == step_id), None)


def _missing(name: str):
    def fail(_state: GraphState) -> dict[str, object]:
        raise RuntimeError(f"graph node {name!r} is not configured")
    return fail


def _submission_route(state: GraphState) -> str:
    return "submit" if state.submit else "offline"


def _entry_route(state: GraphState) -> str:
    return "resume" if state.resume_polling else "new"


def build_generate_song_graph(
    *, nodes: dict[str, Callable[[GraphState], dict[str, object]]] | None = None
):
    """Compile the fixed MVP graph without persistence.

    Concrete orchestration supplies node callables. Missing nodes are explicit
    identities, which keeps graph topology deterministic for tests and adapters.
    """
    implementations = nodes or {}
    builder = StateGraph(GraphState)
    for name in NODE_ORDER + REMOTE_NODE_ORDER:
        builder.add_node(name, implementations.get(name, _missing(name)))
    builder.add_conditional_edges(START, _entry_route, {"new": NODE_ORDER[0], "resume": REMOTE_NODE_ORDER[1]})
    for source, target in zip(NODE_ORDER, NODE_ORDER[1:]):
        builder.add_edge(source, target)
    builder.add_conditional_edges(NODE_ORDER[-1], _submission_route, {"submit": REMOTE_NODE_ORDER[0], "offline": END})
    for source, target in zip(REMOTE_NODE_ORDER, REMOTE_NODE_ORDER[1:]):
        builder.add_edge(source, target)
    builder.add_edge(REMOTE_NODE_ORDER[-1], END)
    return builder.compile(checkpointer=None)
