# ai_ladder_review_v2/ladder_review_agent/nodes/taxonomy_retriever_node.py
from __future__ import annotations

from sqlalchemy.orm import Session

from ..state import LadderReviewState
from ...rag.taxonomy_retriever import TaxonomyRetriever


def taxonomy_retriever_node(
    db: Session,
    state: LadderReviewState,
    *,
    top_k: int = 6,
    taxonomy_version: str = "1.1",
) -> LadderReviewState:
    """
    RAG node:
      - retrieval based only on current batch text
      - if recheck, bias query using checker-provided recheck_query
      - ensure_core=True so boundary/core chunk is included
    """
    batch = state.current_batch()
    if not batch:
        return state

    batch_text = batch["text"]

    query_for_retrieval = batch_text
    if state.batch_retry_count > 0 and state.recheck_query.strip():
        query_for_retrieval = f"{batch_text}\n\nFOCUS:\n{state.recheck_query.strip()}"

    retriever = TaxonomyRetriever()
    chunks = retriever.retrieve(
        db,
        query=query_for_retrieval,
        version=taxonomy_version,
        k=top_k,
        ensure_core=True,
    )

    state.retrieved_taxonomy_titles = [c.title for c in chunks]
    state.taxonomy_context_text = "\n\n".join(
        f"### {c.title}\n{c.content}".strip() for c in chunks
    )

    state.log_trace(
        "taxonomy_retriever",
        {
            "batch_id": batch.get("batch_id"),
            "retry": state.batch_retry_count,
            "retrieved_titles": state.retrieved_taxonomy_titles,
            "query_bias_used": bool(state.batch_retry_count > 0 and state.recheck_query.strip()),
        },
    )
    return state