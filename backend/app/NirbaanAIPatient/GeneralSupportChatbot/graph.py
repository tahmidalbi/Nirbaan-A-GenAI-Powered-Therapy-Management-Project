from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState

from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.db_picker import db_picker_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.session_summarizer import session_summarizer_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.refine_query import refine_query_node
from app.NirbaanAIPatient.GeneralSupportChatbot.Nodes.kb_retrieval import kb_retrieval_node
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


@lru_cache(maxsize=1)
def build_general_support_graph():
    """
    Build and compile the LangGraph for the general support chatbot.
    """

    builder = StateGraph(GeneralSupportState)

    # Nodes
    builder.add_node("db_picker", _db_picker_wrapper)
    builder.add_node("session_summarizer", session_summarizer_node)
    builder.add_node("refine_query", refine_query_node)
    builder.add_node("kb_retrieval", kb_retrieval_node)
    builder.add_node("generate", generate_node)

    # Linear flow
    builder.add_edge(START, "db_picker")
    builder.add_edge("db_picker", "session_summarizer")
    builder.add_edge("session_summarizer", "refine_query")
    builder.add_edge("refine_query", "kb_retrieval")
    builder.add_edge("kb_retrieval", "generate")
    builder.add_edge("generate", END)

    return builder.compile()


general_support_graph = build_general_support_graph()