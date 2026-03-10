from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.NirbaanAITherapist.state import NirbaanAITherapistState


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
PGVECTOR_CONNECTION = os.getenv("PGVECTOR_CONNECTION", os.getenv("DATABASE_URL", ""))
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "therapist_kb")

THERAPIST_RAG_TOP_K = int(os.getenv("THERAPIST_RAG_TOP_K", "6"))
THERAPIST_RAG_FETCH_K = int(os.getenv("THERAPIST_RAG_FETCH_K", "20"))
THERAPIST_RAG_LAMBDA = float(os.getenv("THERAPIST_RAG_LAMBDA", "0.5"))


def retrieve_kb_node(state: NirbaanAITherapistState) -> Dict[str, Any]:
    """
    Retrieve therapist KB chunks relevant to therapist-side patient analysis.
    """

    therapist_id = state["therapist_id"]
    retrieval_query = _build_retrieval_query(state).strip()

    if not retrieval_query:
        return {
            "retrieval_query": "",
            "kb_chunks": [],
            "kb_context_summary": "",
        }

    vector_store = _get_vector_store()

    metadata_filter = {
        "therapist_id": {"$eq": therapist_id}
    }

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": THERAPIST_RAG_TOP_K,
            "fetch_k": max(THERAPIST_RAG_FETCH_K, THERAPIST_RAG_TOP_K),
            "lambda_mult": THERAPIST_RAG_LAMBDA,
            "filter": metadata_filter,
        },
    )

    docs = retriever.invoke(retrieval_query)

    kb_chunks: List[Dict[str, Any]] = []
    for doc in docs:
        metadata = dict(doc.metadata or {})
        kb_chunks.append(
            {
                "content": doc.page_content,
                "source": metadata.get("resource_title", "Unknown Source"),
                "score": 0.0,
                "metadata": metadata,
            }
        )

    return {
        "retrieval_query": retrieval_query,
        "kb_chunks": kb_chunks,
        "kb_context_summary": _build_kb_context_summary(kb_chunks),
    }


def _get_vector_store() -> PGVector:
    if not PGVECTOR_CONNECTION:
        raise ValueError("PGVECTOR_CONNECTION (or DATABASE_URL) is not configured")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    return PGVector(
        embeddings=embeddings,
        collection_name=PGVECTOR_COLLECTION_NAME,
        connection=PGVECTOR_CONNECTION,
        use_jsonb=True,
    )


def _build_retrieval_query(state: NirbaanAITherapistState) -> str:
    """
    Build a therapist-KB retrieval query using:
    - therapist's current chat question
    - optional analysis goal
    - patient context summary
    - clarification question / answer if present
    """

    user_message = (state.get("user_message") or "").strip()
    analysis_goal = (state.get("analysis_goal") or "").strip()
    patient_context_summary = (state.get("patient_context_summary") or "").strip()

    clarification_question = (state.get("clarification_question") or "").strip()
    clarification_answer = (state.get("clarification_answer") or "").strip()

    latest_weekly_progress = state.get("latest_weekly_progress")
    initial_fear_ladder = state.get("initial_fear_ladder")
    obsession_compulsion_pairs = state.get("obsession_compulsion_pairs") or []

    parts: List[str] = []

    if user_message:
        parts.append(f"therapist request: {user_message}")

    if analysis_goal:
        parts.append(f"analysis goal: {analysis_goal}")

    if clarification_question:
        parts.append(f"clarification question: {clarification_question}")

    if clarification_answer:
        parts.append(f"therapist clarification answer: {clarification_answer}")

    if latest_weekly_progress:
        detailed_progress = (latest_weekly_progress.get("detailed_progress") or "").strip()
        homework_reflection = (latest_weekly_progress.get("homework_reflection") or "").strip()

        if detailed_progress:
            parts.append(f"latest weekly progress: {detailed_progress}")
        if homework_reflection:
            parts.append(f"homework reflection: {homework_reflection}")

    if initial_fear_ladder:
        ladder_items = initial_fear_ladder.get("items") or []
        if ladder_items:
            ladder_text = " ; ".join(
                f"{item.get('item')} (SUDS {item.get('suds')})"
                for item in ladder_items[:8]
                if item.get("item")
            )
            if ladder_text:
                parts.append(f"initial fear ladder: {ladder_text}")

    if obsession_compulsion_pairs:
        pair_texts: List[str] = []
        for pair in obsession_compulsion_pairs[:8]:
            obsession = (pair.get("obsession") or "").strip()
            compulsions = pair.get("compulsions") or []

            comp_text = ", ".join(
                str(c).strip()
                for c in compulsions
                if c and str(c).strip()
            )

            if obsession and comp_text:
                pair_texts.append(f"{obsession} -> {comp_text}")
            elif obsession:
                pair_texts.append(obsession)

        if pair_texts:
            parts.append("obsession-compulsion pairs: " + " ; ".join(pair_texts))

    if patient_context_summary:
        parts.append(f"patient context summary: {patient_context_summary}")

    return " | ".join(part for part in parts if part).strip()


def _build_kb_context_summary(kb_chunks: List[Dict[str, Any]]) -> str:
    """
    Create a compact readable summary of retrieved KB chunks for downstream nodes.
    """
    if not kb_chunks:
        return ""

    parts: List[str] = []

    for idx, chunk in enumerate(kb_chunks[:6], start=1):
        source = (chunk.get("source") or "Unknown Source").strip()
        content = (chunk.get("content") or "").strip()
        metadata = chunk.get("metadata") or {}

        location_bits: List[str] = []

        source_type = metadata.get("source_type")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        if source_type:
            location_bits.append(str(source_type))

        if page_start and page_end:
            if page_start == page_end:
                location_bits.append(f"page {page_start}")
            else:
                location_bits.append(f"pages {page_start}-{page_end}")
        elif page_start:
            location_bits.append(f"page {page_start}")

        location_suffix = f" ({', '.join(location_bits)})" if location_bits else ""

        shortened = content[:500].strip()
        if len(content) > 500:
            shortened += "..."

        parts.append(
            f"[KB Source {idx}: {source}{location_suffix}]\n{shortened}"
        )

    return "\n\n---\n\n".join(parts)