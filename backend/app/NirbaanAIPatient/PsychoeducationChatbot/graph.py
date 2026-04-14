from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal
from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.db_picker import db_picker_node
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.session_summarizer import (
    session_summarizer_node,
)
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.kb_retrieval import (
    kb_retrieval_node,
)
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.sufficiency_checker import (
    sufficiency_checker_node,
)
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.sufficiency_router import (
    sufficiency_router,
)
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.web_search import (
    web_search_node,
)
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.generate import (
    generate_node,
)


def _with_db(node_fn):
    """
    Wrap a node so it gets a fresh SQLAlchemy session.
    Use this only for nodes that need DB access.
    """

    def wrapped(state: PsychoeducationState) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            return node_fn(state, db)
        finally:
            db.close()

    return wrapped


def build_psychoeducation_graph():
    graph = StateGraph(PsychoeducationState)

    # Nodes
    graph.add_node("db_picker", _with_db(db_picker_node))
    graph.add_node("session_summarizer", session_summarizer_node)
    graph.add_node("kb_retrieval", kb_retrieval_node)
    graph.add_node("sufficiency_checker", sufficiency_checker_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate", generate_node)

    # Main flow
    graph.add_edge(START, "db_picker")
    graph.add_edge("db_picker", "session_summarizer")
    graph.add_edge("session_summarizer", "kb_retrieval")
    graph.add_edge("kb_retrieval", "sufficiency_checker")

    # Conditional routing after sufficiency check
    graph.add_conditional_edges(
        "sufficiency_checker",
        sufficiency_router,
        {
            "generate": "generate",
            "refine_query": "kb_retrieval",
            "web_search": "web_search",
        },
    )

    # Web fallback then generate
    graph.add_edge("web_search", "generate")

    # End
    graph.add_edge("generate", END)

    return graph.compile()


psychoeducation_graph = build_psychoeducation_graph()


def invoke_psychoeducation_graph(initial_state: PsychoeducationState) -> PsychoeducationState:
    """
    Entry point used by chat_service.py
    """
    return psychoeducation_graph.invoke(initial_state)