from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal

from app.NirbaanAITherapist.state import NirbaanAITherapistState

from app.NirbaanAITherapist.Nodes.load_patient_context import load_patient_context_node
from app.NirbaanAITherapist.Nodes.retrieve_kb import retrieve_kb_node
from app.NirbaanAITherapist.Nodes.analyze_patient import analyze_patient_node
from app.NirbaanAITherapist.Nodes.resume_with_clarification import (
    resume_with_clarification_node,
)
from app.NirbaanAITherapist.Nodes.finalize_analysis import finalize_analysis_node


def _load_patient_context_wrapper(
    state: NirbaanAITherapistState,
) -> Dict[str, Any]:
    """
    Wrapper so DB session is managed outside the node.
    """
    db = SessionLocal()
    try:
        return load_patient_context_node(state, db)
    finally:
        db.close()


def _analysis_router(state: NirbaanAITherapistState) -> str:
    """
    Route directly after analyze_patient.

    If clarification is needed, stop the graph and return state to backend.
    If not, finalize analysis.
    """
    if state.get("needs_clarification", False):
        return "end_for_clarification"

    return "finalize"


@lru_cache(maxsize=1)
def build_therapist_analysis_graph():
    """
    Initial therapist-analysis graph.

    Flow:
    START
      -> load_patient_context
      -> retrieve_kb
      -> analyze_patient
         -> finalize_analysis -> END
         -> END (if clarification needed)
    """
    builder = StateGraph(NirbaanAITherapistState)

    builder.add_node("load_patient_context", _load_patient_context_wrapper)
    builder.add_node("retrieve_kb", retrieve_kb_node)
    builder.add_node("analyze_patient", analyze_patient_node)
    builder.add_node("finalize_analysis", finalize_analysis_node)

    builder.add_edge(START, "load_patient_context")
    builder.add_edge("load_patient_context", "retrieve_kb")
    builder.add_edge("retrieve_kb", "analyze_patient")

    builder.add_conditional_edges(
        "analyze_patient",
        _analysis_router,
        {
            "finalize": "finalize_analysis",
            "end_for_clarification": END,
        },
    )

    builder.add_edge("finalize_analysis", END)

    return builder.compile()


@lru_cache(maxsize=1)
def build_resume_therapist_analysis_graph():
    """
    Resume graph after therapist answers clarification.

    Flow:
    START
      -> resume_with_clarification
      -> finalize_analysis
      -> END
    """
    builder = StateGraph(NirbaanAITherapistState)

    builder.add_node("resume_with_clarification", resume_with_clarification_node)
    builder.add_node("finalize_analysis", finalize_analysis_node)

    builder.add_edge(START, "resume_with_clarification")
    builder.add_edge("resume_with_clarification", "finalize_analysis")
    builder.add_edge("finalize_analysis", END)

    return builder.compile()


therapist_analysis_graph = build_therapist_analysis_graph()
resume_therapist_analysis_graph = build_resume_therapist_analysis_graph()


def invoke_therapist_analysis_graph(
    initial_state: NirbaanAITherapistState,
) -> NirbaanAITherapistState:
    """
    Entry point for first-pass therapist analysis.
    """
    return therapist_analysis_graph.invoke(initial_state)


def invoke_resume_therapist_analysis_graph(
    resume_state: NirbaanAITherapistState,
) -> NirbaanAITherapistState:
    """
    Entry point for resuming analysis after therapist clarification answer.
    """
    return resume_therapist_analysis_graph.invoke(resume_state)