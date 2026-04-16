# app/education/relapse_prevention/models.py
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database.base import Base


class RelapsePreventionEducationCache(Base):
    """Stores generated relapse prevention education content for patients."""
    __tablename__ = "relapse_prevention_education_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    topic: Mapped[str] = mapped_column(String, nullable=False)
    reading_level: Mapped[str] = mapped_column(String, default="simple")
    sections_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sources_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
