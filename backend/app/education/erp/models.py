# app/education/erp/models.py
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database.base import Base


class ERPEducationCache(Base):
    """Stores generated ERP education content for patients."""
    __tablename__ = "erp_education_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        unique=True,  # One education entry per patient
        index=True,
    )

    # Full education content
    topic: Mapped[str] = mapped_column(String, nullable=False)
    reading_level: Mapped[str] = mapped_column(String, default="simple")
    sections_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sources_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
