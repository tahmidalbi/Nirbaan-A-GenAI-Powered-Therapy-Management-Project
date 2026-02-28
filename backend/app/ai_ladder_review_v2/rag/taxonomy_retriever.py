# ai_ladder_review_v2/rag/taxonomy_retriever.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .constants import (
    CORE_CHUNK_TAG,
    CORE_CHUNK_TITLE,
    DEFAULT_TOP_K,
    TAXONOMY_VERSION_DEFAULT,
)
from .embedding_client import EmbeddingClient
from .taxonomy_model import TaxonomyChunk


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    version: str
    title: str
    tags: List[str]
    content: str


class TaxonomyRetriever:
    """
    Small-taxonomy RAG retriever.

    Design goals:
    - Use vector similarity to fetch the most relevant taxonomy chunks for a query.
    - Always include the Core rules chunk (or core-tag chunk) so the LLM follows boundaries.
    - Keep output small and stable (top-k, deduped).

    Notes:
    - This class embeds the query text and performs a vector similarity search in Postgres pgvector.
    - Requires the taxonomy_chunks table to be seeded with embeddings.
    """

    def __init__(self, embedder: Optional[EmbeddingClient] = None):
        self._embedder = embedder or EmbeddingClient()

    def retrieve(
        self,
        db: Session,
        *,
        query: str,
        version: str = TAXONOMY_VERSION_DEFAULT,
        k: int = DEFAULT_TOP_K,
        ensure_core: bool = True,
    ) -> List[RetrievedChunk]:
        """
        Returns up to k chunks (plus core if ensure_core and not already included).
        """
        query = (query or "").strip()
        if not query:
            # If query is empty, just return core (and optionally one or two general chunks).
            rows = self._get_core_rows(db, version)
            return [self._to_out(r) for r in rows]

        q_emb = self._embedder.embed_text(query)

        # Cosine distance ordering (requires pgvector operator class vector_cosine_ops at index time).
        # pgvector.sqlalchemy supports: TaxonomyChunk.embedding.cosine_distance(q_emb)
        stmt = (
            select(TaxonomyChunk)
            .where(TaxonomyChunk.version == version)
            .order_by(TaxonomyChunk.embedding.cosine_distance(q_emb))
            .limit(k)
        )
        rows = db.execute(stmt).scalars().all()

        out = [self._to_out(r) for r in rows]

        if ensure_core:
            out = self._ensure_core(db, out, version)

        # Dedup by title (just in case)
        out = self._dedup_by_title(out)

        return out

    def retrieve_many(
        self,
        db: Session,
        *,
        queries: Sequence[str],
        version: str = TAXONOMY_VERSION_DEFAULT,
        k_per_query: int = 3,
        max_total: int = 10,
        ensure_core: bool = True,
    ) -> List[RetrievedChunk]:
        """
        Retrieve across multiple queries and merge:
        - Useful for a log batch where you want to query "somatic", "rumination", "reassurance", etc.
        - Dedup by title
        - Respect max_total
        """
        merged: List[RetrievedChunk] = []
        for q in queries:
            chunks = self.retrieve(db, query=q, version=version, k=k_per_query, ensure_core=False)
            merged.extend(chunks)

        merged = self._dedup_by_title(merged)

        if ensure_core:
            merged = self._ensure_core(db, merged, version)

        # cap total
        return merged[:max_total]

    # -------------------------
    # Internals
    # -------------------------

    def _ensure_core(self, db: Session, current: List[RetrievedChunk], version: str) -> List[RetrievedChunk]:
        titles = {c.title for c in current}
        if CORE_CHUNK_TITLE in titles:
            return current

        # Try exact title
        core_rows = self._get_core_rows(db, version)
        if core_rows:
            core_out = [self._to_out(r) for r in core_rows]
            return core_out + current

        # Fallback: by tag "core"
        stmt = (
            select(TaxonomyChunk)
            .where(TaxonomyChunk.version == version)
            .where(TaxonomyChunk.tags.contains([CORE_CHUNK_TAG]))
            .limit(1)
        )
        row = db.execute(stmt).scalars().first()
        if row:
            return [self._to_out(row)] + current

        # If no core exists, return as-is.
        return current

    def _get_core_rows(self, db: Session, version: str) -> List[TaxonomyChunk]:
        stmt = (
            select(TaxonomyChunk)
            .where(TaxonomyChunk.version == version)
            .where(TaxonomyChunk.title == CORE_CHUNK_TITLE)
            .limit(1)
        )
        row = db.execute(stmt).scalars().first()
        return [row] if row else []

    def _dedup_by_title(self, items: List[RetrievedChunk]) -> List[RetrievedChunk]:
        seen = set()
        out: List[RetrievedChunk] = []
        for c in items:
            key = c.title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    def _to_out(self, row: TaxonomyChunk) -> RetrievedChunk:
        return RetrievedChunk(
            id=str(row.id),
            version=row.version,
            title=row.title,
            tags=list(row.tags or []),
            content=row.content,
        )