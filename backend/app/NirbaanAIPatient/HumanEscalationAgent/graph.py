from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal

from app.NirbaanAIPatient.HumanEscalationAgent.state import HumanEscalationState
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.load_context import load_context_node
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.verifier import verifier_node
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.no_help_needed import no_help_needed_node
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.generate_helper_message import generate_helper_message_node
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.send_to_ep_group import send_to_ep_group_node


# ── DB-aware wrappers ────────────────────────────────────────────────────────

def _load_context_wrapper(state: HumanEscalationState) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        return load_context_node(state, db)
    finally:
        db.close()


def _send_to_ep_group_wrapper(state: HumanEscalationState) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        return send_to_ep_group_node(state, db)
    finally:
        db.close()


# ── Router function ──────────────────────────────────────────────────────────

def verifier_decision(state: HumanEscalationState) -> str:
    if state.get("needs_human_help"):
        return "generate_helper_message"
    return "no_help_needed"


# ── Build graph ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def build_human_escalation_graph():
    builder = StateGraph(HumanEscalationState)

    # Nodes
    builder.add_node("load_context", _load_context_wrapper)
    builder.add_node("verifier", verifier_node)
    builder.add_node("no_help_needed", no_help_needed_node)
    builder.add_node("generate_helper_message", generate_helper_message_node)
    builder.add_node("send_to_ep_group", _send_to_ep_group_wrapper)

    # Edges
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "verifier")

    builder.add_conditional_edges(
        "verifier",
        verifier_decision,
        {
            "generate_helper_message": "generate_helper_message",
            "no_help_needed": "no_help_needed",
        },
    )

    builder.add_edge("generate_helper_message", "send_to_ep_group")
    builder.add_edge("send_to_ep_group", END)
    builder.add_edge("no_help_needed", END)

    return builder.compile()


human_escalation_graph = build_human_escalation_graph()
