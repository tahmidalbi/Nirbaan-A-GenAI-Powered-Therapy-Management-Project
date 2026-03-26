from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.NirbaanAIPatient.GeneralSupportChatbot.state import (
    GeneralSupportState,
    RetrievedChunk,
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

PGVECTOR_CONNECTION = os.getenv("PGVECTOR_CONNECTION", os.getenv("DATABASE_URL", ""))
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "therapist_kb")

# Retrieval tuning
RAG_TOP_K = int(os.getenv("RAG_TOP_K_DEFAULT", "6"))
RAG_FETCH_K = int(os.getenv("RAG_MMR_FETCH_K", "20"))
RAG_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.5"))


def kb_retrieval_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Retrieve therapist knowledge base chunks using the refined retrieval query.
    """

    retrieval_query = (state.get("retrieval_query") or "").strip()
    therapist_id = state.get("therapist_id")

    if not retrieval_query:
        return {
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
            "k": RAG_TOP_K,
            "fetch_k": max(RAG_FETCH_K, RAG_TOP_K),
            "lambda_mult": RAG_LAMBDA,
            "filter": metadata_filter,
        },
    )

    docs = retriever.invoke(retrieval_query)

    chunks: List[RetrievedChunk] = []

    for doc in docs:
        metadata = dict(doc.metadata or {})

        chunks.append(
            {
                "content": doc.page_content,
                "source": metadata.get("resource_title", "Unknown Source"),
                "score": 0.0,  # MMR does not return similarity score
                "metadata": metadata,
            }
        )

    context_summary = _build_context_summary(chunks)

    return {
        "kb_chunks": chunks,
        "kb_context_summary": context_summary,
    }


def _get_vector_store() -> PGVector:
    if not PGVECTOR_CONNECTION:
        raise ValueError("PGVECTOR_CONNECTION (or DATABASE_URL) not configured")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    return PGVector(
        embeddings=embeddings,
        collection_name=PGVECTOR_COLLECTION_NAME,
        connection=PGVECTOR_CONNECTION,
        use_jsonb=True,
    )


def _build_context_summary(chunks: List[RetrievedChunk]) -> str:
    """
    Create a compact context summary for downstream nodes.
    """

    if not chunks:
        return ""

    parts: List[str] = []

    for idx, chunk in enumerate(chunks[:6], start=1):
        source = chunk.get("source") or "Unknown"
        text = (chunk.get("content") or "").strip()

        if len(text) > 400:
            text = text[:400] + "..."

        parts.append(f"[Source {idx}: {source}]\n{text}")

    return "\n\n---\n\n".join(parts)