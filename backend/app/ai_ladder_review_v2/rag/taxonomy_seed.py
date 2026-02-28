# ai_ladder_review_v2/rag/taxonomy_seed.py
"""
One-time (or versioned) seeding script:
- Reads manual taxonomy chunks from taxonomy.py
- Embeds each chunk using OpenAI embeddings
- Upserts into Postgres (pgvector) table taxonomy_chunks

How to run (from backend/):
  python -m app.ai_ladder_review_v2.rag.taxonomy_seed

Requirements:
- Postgres with pgvector extension enabled: CREATE EXTENSION IF NOT EXISTS vector;
- SQLAlchemy engine/session available (see DATABASE_URL)
- OPENAI_API_KEY set
"""

from __future__ import annotations

import os
from typing import Tuple

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, text

from app.database.session import engine, SessionLocal
from .embedding_client import EmbeddingClient
from .taxonomy_chunks import get_taxonomy_chunks, get_taxonomy_version
from .taxonomy_model import TaxonomyChunk, Base


# Embed f"{title}\n\n{content}" so the title helps retrieval.
def _make_embed_text(title: str, content: str) -> str:
    return f"{title}\n\n{content}".strip()


def _chunk_key(version: str, title: str) -> Tuple[str, str]:
    return (version.strip(), title.strip().lower())


def seed_taxonomy(*, create_tables_if_missing: bool = False) -> None:
    version = get_taxonomy_version()
    chunks = get_taxonomy_chunks()

    if create_tables_if_missing:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(engine)

    embedder = EmbeddingClient()

    # Preload existing (version,title) to make it idempotent
    with SessionLocal() as db:
        existing = db.execute(
            select(TaxonomyChunk).where(TaxonomyChunk.version == version)
        ).scalars().all()

        existing_map = {_chunk_key(row.version, row.title): row for row in existing}

        inserted = 0
        updated = 0

        for ch in chunks:
            title = str(ch["title"]).strip()
            content = str(ch["content"]).strip()
            tags = list(ch.get("tags", []))

            key = _chunk_key(version, title)
            embed_text = _make_embed_text(title, content)

            embedding = embedder.embed_text(embed_text)

            row = existing_map.get(key)
            if row is None:
                row = TaxonomyChunk(
                    version=version,
                    title=title,
                    tags=tags,
                    content=content,
                    embedding=embedding,
                )
                db.add(row)
                inserted += 1
            else:
                # Update content/tags/embedding if changed (safe to always update)
                row.tags = tags
                row.content = content
                row.embedding = embedding
                updated += 1

        db.commit()

    print(f"[taxonomy_seed] version={version} inserted={inserted} updated={updated}")


if __name__ == "__main__":
    # Set to True if you don't have migrations yet and want auto table create.
    # In production, prefer Alembic migrations instead.
    seed_taxonomy(create_tables_if_missing=True)