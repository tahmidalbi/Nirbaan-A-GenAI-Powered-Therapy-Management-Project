# ai_ladder_review_v2/ladder_review_agent/graph.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, Optional, Tuple

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from .state import LadderReviewState

from .nodes.load_context import load_context_node
from .nodes.ladder_extractor import ladder_extractor_node
from .nodes.create_batches import create_batches_node
from .nodes.taxonomy_retriever_node import taxonomy_retriever_node
from .nodes.symtom_finder import symptom_finder_node
from .nodes.checker import checker_node
from .nodes.hidden_matcher import hidden_matcher_node
from .nodes.finalizer import finalizer_node

from app.fear_ladder.models import AILadderReview, AILadderReviewStatus


StateDict = Dict[str, Any]


def _to_state(d: StateDict) -> LadderReviewState:
    """Convert a dict coming from LangGraph into our dataclass state."""
    return LadderReviewState(**d)


def _to_dict(s: LadderReviewState) -> StateDict:
    """Convert our dataclass state back into a dict for LangGraph."""
    return asdict(s)


def _wrap_no_db(fn: Callable[[LadderReviewState], LadderReviewState]) -> Callable[[StateDict], StateDict]:
    """Adapter: LangGraph dict -> dataclass -> node -> dict."""
    def _inner(d: StateDict) -> StateDict:
        st = _to_state(d)
        st = fn(st)
        return _to_dict(st)
    return _inner


def _wrap_with_db(fn: Callable[[Session, LadderReviewState], LadderReviewState], db: Session) -> Callable[[StateDict], StateDict]:
    """Adapter for nodes that need a DB session."""
    def _inner(d: StateDict) -> StateDict:
        st = _to_state(d)
        st = fn(db, st)
        return _to_dict(st)
    return _inner


def build_ladder_review_graph(
    *,
    db: Session,
    taxonomy_version: str = "1.1",
    taxonomy_top_k: int = 6,
    max_entries_per_batch: int = 40,
) -> Any:
    """
    Builds and compiles the LangGraph for:
      load_context (no LLM) ->
      ladder_extractor (LLM) ->
      create_batches (no LLM) ->
      loop over batches:
          taxonomy_retriever (RAG) ->
          symptom_finder (LLM) ->
          checker (LLM) ->
          (recheck same batch up to max_batch_retries) OR next batch
      hidden_matcher (LLM) ->
      finalizer (no LLM + DB writes)
    """

    graph = StateGraph(StateDict)

    # ---------------------------
    # Small helper nodes
    # ---------------------------

    def mark_review_running_node(d: StateDict) -> StateDict:
        st = _to_state(d)
        if not st.review_id:
            raise RuntimeError("state.review_id is required")

        review = db.get(AILadderReview, int(st.review_id))
        if not review:
            raise RuntimeError(f"AILadderReview not found id={st.review_id}")

        review.status = AILadderReviewStatus.running
        review.error_message = None
        db.commit()

        st.log_trace("mark_review_running", {"review_id": st.review_id})
        return _to_dict(st)

    def taxonomy_retriever_configured(d: StateDict) -> StateDict:
        st = _to_state(d)
        st = taxonomy_retriever_node(
            db,
            st,
            top_k=taxonomy_top_k,
            taxonomy_version=taxonomy_version,
        )
        return _to_dict(st)

    def create_batches_configured(d: StateDict) -> StateDict:
        st = _to_state(d)
        st = create_batches_node(st, max_entries_per_batch=max_entries_per_batch)
        return _to_dict(st)

    def advance_or_recheck_router(d: StateDict) -> str:
        """
        Routes after checker:
          - If recheck == True and retry_count < max -> re-run retriever for SAME batch
          - Else advance to next batch; if done -> hidden_matcher else retriever
        """
        st = _to_state(d)
        batch = st.current_batch()

        # If no batch at all, jump to hidden matcher
        if not batch:
            return "hidden_matcher"

        if st.recheck and st.batch_retry_count < st.max_batch_retries:
            return "recheck_same_batch"

        return "advance_batch"

    def recheck_same_batch_node(d: StateDict) -> StateDict:
        """
        Increment retry count (same batch), keep batch_index.
        """
        st = _to_state(d)
        st.batch_retry_count += 1
        st.log_trace("recheck_same_batch", {
            "batch_id": (st.current_batch() or {}).get("batch_id"),
            "batch_retry_count": st.batch_retry_count,
            "max_batch_retries": st.max_batch_retries,
            "recheck_reason": st.recheck_reason,
            "recheck_query": st.recheck_query,
        })
        return _to_dict(st)

    def advance_batch_node(d: StateDict) -> StateDict:
        """
        Move to next batch; reset retry + recheck fields.
        """
        st = _to_state(d)
        st.batch_index += 1
        st.batch_retry_count = 0
        st.recheck = False
        st.recheck_reason = ""
        st.recheck_query = ""
        st.batch_candidates = []
        st.taxonomy_context_text = ""
        st.retrieved_taxonomy_titles = []
        st.log_trace("advance_batch", {
            "next_batch_index": st.batch_index,
            "batches_total": len(st.batches or []),
        })
        return _to_dict(st)

    def after_advance_router(d: StateDict) -> str:
        """
        After advancing, either:
          - if more batches -> taxonomy retriever
          - else -> hidden_matcher
        """
        st = _to_state(d)
        if st.is_done():
            return "hidden_matcher"
        return "taxonomy_retriever"

    def finalizer_configured(d: StateDict) -> StateDict:
        st = _to_state(d)
        st = finalizer_node(db, st)
        return _to_dict(st)

    # ---------------------------
    # Register nodes
    # ---------------------------

    graph.add_node("mark_review_running", mark_review_running_node)
    graph.add_node("load_context", _wrap_with_db(load_context_node, db))
    graph.add_node("ladder_extractor", _wrap_no_db(ladder_extractor_node))
    graph.add_node("create_batches", create_batches_configured)

    graph.add_node("taxonomy_retriever", taxonomy_retriever_configured)
    graph.add_node("symptom_finder", _wrap_no_db(symptom_finder_node))
    graph.add_node("checker", _wrap_no_db(checker_node))

    graph.add_node("recheck_same_batch", recheck_same_batch_node)
    graph.add_node("advance_batch", advance_batch_node)

    graph.add_node("hidden_matcher", _wrap_no_db(hidden_matcher_node))
    graph.add_node("finalizer", finalizer_configured)

    # ---------------------------
    # Edges
    # ---------------------------

    graph.set_entry_point("mark_review_running")
    graph.add_edge("mark_review_running", "load_context")
    graph.add_edge("load_context", "ladder_extractor")
    graph.add_edge("ladder_extractor", "create_batches")

    # If no batches, go straight to hidden matcher; otherwise go to taxonomy retriever
    def after_create_batches_router(d: StateDict) -> str:
        st = _to_state(d)
        return "taxonomy_retriever" if (st.batches and len(st.batches) > 0) else "hidden_matcher"

    graph.add_conditional_edges(
        "create_batches",
        after_create_batches_router,
        {
            "taxonomy_retriever": "taxonomy_retriever",
            "hidden_matcher": "hidden_matcher",
        },
    )

    # Per-batch chain
    graph.add_edge("taxonomy_retriever", "symptom_finder")
    graph.add_edge("symptom_finder", "checker")

    # Checker decides recheck or advance
    graph.add_conditional_edges(
        "checker",
        advance_or_recheck_router,
        {
            "recheck_same_batch": "recheck_same_batch",
            "advance_batch": "advance_batch",
            "hidden_matcher": "hidden_matcher",
        },
    )

    # If recheck same batch, go back to retriever (same batch, biased query)
    graph.add_edge("recheck_same_batch", "taxonomy_retriever")

    # If advance batch, route to next batch or hidden matcher
    graph.add_conditional_edges(
        "advance_batch",
        after_advance_router,
        {
            "taxonomy_retriever": "taxonomy_retriever",
            "hidden_matcher": "hidden_matcher",
        },
    )

    # Finish
    graph.add_edge("hidden_matcher", "finalizer")
    graph.add_edge("finalizer", END)

    return graph.compile()


def run_ladder_review_agent(
    *,
    db_session_factory: Callable[[], Session],
    review_id: int,
    taxonomy_version: str = "1.1",
    taxonomy_top_k: int = 6,
    max_entries_per_batch: int = 40,
) -> Dict[str, Any]:
    """
    Convenience runner (good for Celery):
      - opens one DB session
      - runs the graph
      - closes the session
      - returns final state's result_payload
    """
    db = db_session_factory()
    try:
        app = build_ladder_review_graph(
            db=db,
            taxonomy_version=taxonomy_version,
            taxonomy_top_k=taxonomy_top_k,
            max_entries_per_batch=max_entries_per_batch,
        )

        initial: Dict[str, Any] = {
            "review_id": str(review_id),
        }

        final_state: Dict[str, Any] = app.invoke(initial)
        # finalizer_node fills result_payload
        return final_state.get("result_payload", {}) or {}
    except Exception as e:
        # Best-effort: mark review failed
        try:
            review = db.get(AILadderReview, int(review_id))
            if review:
                review.status = AILadderReviewStatus.failed
                review.error_message = str(e)
                db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()