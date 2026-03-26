from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
PGVECTOR_CONNECTION = os.getenv("PGVECTOR_CONNECTION", os.getenv("DATABASE_URL", ""))
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "therapist_kb")

RAG_TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K_DEFAULT", "6"))
RAG_MMR_FETCH_K = int(os.getenv("RAG_MMR_FETCH_K", "20"))
RAG_MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.5"))


class PsychoeducationKBService:
    """
    Therapist-KB retrieval service using LangChain PGVector + MMR retriever.
    """

    def __init__(self) -> None:
        if not PGVECTOR_CONNECTION:
            raise ValueError("PGVECTOR_CONNECTION (or DATABASE_URL) is not configured")

        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=PGVECTOR_COLLECTION_NAME,
            connection=PGVECTOR_CONNECTION,
            use_jsonb=True,
        )

    def _build_filter(self, therapist_id: int) -> Dict[str, Any]:
        return {
            "therapist_id": {"$eq": therapist_id}
        }

    def retrieve_chunks(
        self,
        *,
        therapist_id: int,
        query: str,
        top_k: int = RAG_TOP_K_DEFAULT,
    ) -> List[Dict[str, Any]]:
        metadata_filter = self._build_filter(therapist_id=therapist_id)

        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": top_k,
                "fetch_k": max(top_k, RAG_MMR_FETCH_K),
                "lambda_mult": RAG_MMR_LAMBDA,
                "filter": metadata_filter,
            },
        )

        docs = retriever.invoke(query)

        chunks: List[Dict[str, Any]] = []
        for doc in docs:
            metadata = dict(doc.metadata or {})
            chunks.append(
                {
                    "content": doc.page_content,
                    "source": metadata.get("resource_title", "Untitled"),
                    "score": 0.0,  # LangChain MMR retriever doesn't expose score here
                    "metadata": metadata,
                }
            )

        return chunks


def kb_retrieval_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Retrieve therapist KB chunks using the retrieval query prepared by context_selector.py.

    Inputs expected in state:
    - therapist_id
    - retrieval_query

    Outputs:
    - kb_chunks
    - kb_context_summary
    """
    therapist_id = state["therapist_id"]
    retrieval_query = (state.get("retrieval_query") or "").strip()

    if not retrieval_query:
        return {
            "kb_chunks": [],
            "kb_context_summary": "",
        }

    service = PsychoeducationKBService()
    chunks = service.retrieve_chunks(
        therapist_id=therapist_id,
        query=retrieval_query,
        top_k=RAG_TOP_K_DEFAULT,
    )

    kb_context_summary = _build_kb_context_summary(chunks)

    return {
        "kb_chunks": chunks,
        "kb_context_summary": kb_context_summary,
    }


def _build_kb_context_summary(chunks: List[Dict[str, Any]]) -> str:
    """
    Builds a compact human-readable summary of retrieved KB chunks for downstream nodes.
    """
    if not chunks:
        return ""

    lines: List[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        content = (chunk.get("content") or "").strip()
        source = (chunk.get("source") or "Untitled").strip()
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

        shortened_content = content[:500].strip()
        if len(content) > 500:
            shortened_content += "..."

        lines.append(
            f"[KB Source {idx}: {source}{location_suffix}]\n{shortened_content}"
        )

    return "\n\n---\n\n".join(lines)