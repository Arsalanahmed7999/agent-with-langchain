"""One small LangGraph workflow with a bounded review path.

START -> router -> general | study -> reviewer -> END
                                         |  (improve, only if revision_count == 0)
                                         v
                                      improver -> reviewer

A node is a focused piece of work, not automatically an agent. The router is
ordinary Python. The answer, reviewer, and improver nodes each call one
LangChain chain. The improver runs at most once.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from learning_companion.chain import (
    build_chain,
    build_improve_chain,
    build_review_chain,
    build_study_chain,
    select_route,
)
from learning_companion.settings import Settings

USAGE_HINT = "Add a question after /study, for example: /study Explain what an API is."
MAX_REVISIONS = 1


class RouteState(TypedDict):
    user_message: str  # latest user message (marker removed once routed)
    messages: list  # earlier messages, already converted by build_history()
    route: str  # "general" or "study"; empty until the router writes it
    draft_answer: str  # answer written by an answer node, not yet reviewed
    review_decision: str  # "approve" or "improve", written by the reviewer
    review_reason: str  # one short sentence from the reviewer
    revision_count: int  # times the improver has run; maximum 1
    final_answer: str  # the answer sent to Open WebUI


def router_node(state: RouteState) -> dict:
    """Ordinary Python, no model call: keeps the /study rule."""
    route, question = select_route(state["user_message"])
    return {"route": route, "user_message": question}


def after_reviewer(state: RouteState) -> str:
    """Bounded edge: improve only while revision_count is below the limit."""
    if (
        state["review_decision"] == "improve"
        and state["revision_count"] < MAX_REVISIONS
    ):
        return "improver"
    return "end"


def build_graph(settings: Settings):
    """Raises ConfigError (from the chain builders) if key or model is missing."""
    general_chain = build_chain(settings)
    study_chain = build_study_chain(settings)
    review_chain = build_review_chain(settings)
    improve_chain = build_improve_chain(settings)

    def general_node(state: RouteState) -> dict:
        inputs = {"history": state["messages"], "question": state["user_message"]}
        return {"draft_answer": general_chain.invoke(inputs)}

    def study_node(state: RouteState) -> dict:
        if not state["user_message"]:
            # Usage hint: nothing to review.
            return {"draft_answer": USAGE_HINT, "review_decision": "approve"}
        inputs = {"history": state["messages"], "question": state["user_message"]}
        return {"draft_answer": study_chain.invoke(inputs)}

    def reviewer_node(state: RouteState) -> dict:
        draft = state["draft_answer"]
        # Hint, or the one allowed revision is used up: accept the draft as final.
        if (
            state["review_decision"] == "approve"
            or state["revision_count"] >= MAX_REVISIONS
        ):
            return {"review_decision": "approve", "final_answer": draft}
        verdict = review_chain.invoke({"route": state["route"], "draft": draft})
        update = {"review_decision": verdict.decision, "review_reason": verdict.reason}
        if verdict.decision == "approve":
            update["final_answer"] = draft
        return update

    def improver_node(state: RouteState) -> dict:
        text = improve_chain.invoke(
            {
                "route": state["route"],
                "draft": state["draft_answer"],
                "reason": state["review_reason"],
            }
        )
        return {"draft_answer": text, "revision_count": state["revision_count"] + 1}

    graph = StateGraph(RouteState)
    graph.add_node("router", router_node)
    graph.add_node("general", general_node)
    graph.add_node("study", study_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("improver", improver_node)
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router", lambda state: state["route"], {"general": "general", "study": "study"}
    )
    graph.add_edge("general", "reviewer")
    graph.add_edge("study", "reviewer")
    graph.add_conditional_edges(
        "reviewer", after_reviewer, {"improver": "improver", "end": END}
    )
    graph.add_edge("improver", "reviewer")
    return graph.compile()


def run_graph(graph, user_message: str, history: list):
    """Yield ("route", r), ("text", final_answer), then ("trace", details)."""
    state = {
        "user_message": user_message,
        "messages": history,
        "route": "",
        "draft_answer": "",
        "review_decision": "",
        "review_reason": "",
        "revision_count": 0,
        "final_answer": "",
    }
    nodes: list[str] = []
    decision, revisions = "", 0
    for data in graph.stream(state, stream_mode="updates"):
        for name, update in data.items():
            nodes.append(name)
            decision = update.get("review_decision", decision)
            revisions = update.get("revision_count", revisions)
            if name == "router":
                yield "route", update["route"]
            if update.get("final_answer"):
                yield "text", update["final_answer"]
    yield "trace", {"nodes": nodes, "decision": decision, "revisions": revisions}
