# ai_ladder_review_v2/rag/taxonomy_model.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# pgvector SQLAlchemy type
# Install: pip install pgvector
# Also ensure Postgres extension: CREATE EXTENSION IF NOT EXISTS vector;
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class TaxonomyChunk(Base):
    """
    Stores manually-authored OCD taxonomy chunks for small-taxonomy RAG.

    Notes:
      - embedding dimensionality must match your chosen embedding model.
      - keep versioned chunks so you can safely evolve taxonomy over time.
    """
    __tablename__ = "taxonomy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    version: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # Optional: lightweight hybrid retrieval / debugging
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # IMPORTANT: Set the correct dimension for your embedding model.
    # If you use "text-embedding-3-large", dimension is commonly 3072.
    # If you use "text-embedding-3-small", dimension is commonly 1536.
    # Pick ONE model and keep consistent.
    embedding: Mapped[list[float]] = mapped_column(Vector(3072), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    