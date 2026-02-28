# app/education/ocd_core/models.py
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database.base import Base


class OCDCoreEducationStatus:
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class OCDCoreEducationCache(Base):
    """Stores generated OCD core concepts education content for patients."""
    __tablename__ = "ocd_core_education_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        unique=True,   # one record per patient
        index=True,
    )

    # Async status tracking (driven by Celery)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generated content (null until completed)
    topic: Mapped[str | None] = mapped_column(String, nullable=True)
    reading_level: Mapped[str | None] = mapped_column(String, default="simple", nullable=True)
    sections_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
