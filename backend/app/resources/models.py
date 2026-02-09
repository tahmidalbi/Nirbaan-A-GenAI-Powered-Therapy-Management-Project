from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.database.base import Base
from datetime import datetime

# Import related models to ensure they're registered with SQLAlchemy
# This prevents "NoReferencedTableError" during foreign key resolution
import app.therapists.models  # noqa: F401

class Resource(Base):
    """Knowledge base documents uploaded by therapists"""
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    
    # File metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # R2 storage (S3-compatible)
    r2_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    r2_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, txt, docx
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="initiated")
    # Status values: initiated, uploaded, processing, ready, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Stats
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ResourceChunk(Base):
    """Embedded text chunks from resources"""
    __tablename__ = "resource_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    
    # Chunk data
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata (JSONB for better performance: {page: 12, section: "Introduction"})
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    
    # Vector embedding (1536 dimensions for text-embedding-3-small) - CORRECTED!
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IngestionJob(Base):
    """Track resource ingestion progress"""
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    
    # Job status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    # Status values: queued, running, completed, failed
    
    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    current_step: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Celery task ID
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Logs and errors
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())