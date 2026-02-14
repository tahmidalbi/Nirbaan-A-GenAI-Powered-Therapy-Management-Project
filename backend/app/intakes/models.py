from __future__ import annotations

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database.base import Base
from datetime import datetime


class PatientIntake(Base):
    """Patient intake form with detailed history and issues (OCD-ready)."""
    __tablename__ = "patient_intakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)

    # Story and Background
    your_story: Mapped[str] = mapped_column(Text, nullable=False)
    when_started: Mapped[str] = mapped_column(String(500), nullable=False)

    # Previous Therapy
    tried_previous_therapy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    previous_therapy_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Medication
    taken_medication: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    medication_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Life Impact
    affected_life_areas: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Issues with severity ratings
    # Format: [{"issue": "fear of harm", "severity": 8}, ...]
    issues: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # ---------------------------
    # AI Summary fields
    # ---------------------------
    # pending | running | done | failed
    ai_summary_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # Therapist-facing bullet summary
    ai_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent-friendly structured snapshot
    ai_summary_structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Debugging / maintenance
    ai_summary_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ai_summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
