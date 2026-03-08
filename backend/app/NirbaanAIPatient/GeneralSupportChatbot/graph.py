from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState

from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.db_picker import db_picker_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.context_selector import context_selector_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.refine_query import refine_query_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.kb_retrieval import kb_retrieval_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.sufficiency_checker import sufficiency_checker_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.web_search import web_search_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.generate import generate_node


def _db_picker_wrapper(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Wrapper so db session is managed outside the node.
    """
    db = SessionLocal()
    try:
        return db_picker_node(state, db)
    finally:
        db.close()


def _sufficiency_router(state: GeneralSupportState) -> str:
    """
    Decide whether to go directly to generation or perform web search.
    """

    if state.get("retrieval_sufficient", False):
        return "generate"

    return "web_search"


@lru_cache(maxsize=1)
def build_general_support_graph():
    """
    Build and compile the LangGraph for the general support chatbot.
    """

    builder = StateGraph(GeneralSupportState)

    # Nodes
    builder.add_node("db_picker", _db_picker_wrapper)
    builder.add_node("context_selector", context_selector_node)
    builder.add_node("refine_query", refine_query_node)
    builder.add_node("kb_retrieval", kb_retrieval_node)
    builder.add_node("sufficiency_checker", sufficiency_checker_node)
    builder.add_node("web_search", web_search_node)
    builder.add_node("generate", generate_node)

    # Linear flow
    builder.add_edge(START, "db_picker")
    builder.add_edge("db_picker", "context_selector")
    builder.add_edge("context_selector", "refine_query")
    builder.add_edge("refine_query", "kb_retrieval")
    builder.add_edge("kb_retrieval", "sufficiency_checker")

    # Conditional routing
    builder.add_conditional_edges(
        "sufficiency_checker",
        _sufficiency_router,
        {
            "generate": "generate",
            "web_search": "web_search",
        },
    )

    # Web fallback
    builder.add_edge("web_search", "generate")

    # End
    builder.add_edge("generate", END)

    return builder.compile()


# Singleton graph instance
general_support_graph = build_general_support_graph()