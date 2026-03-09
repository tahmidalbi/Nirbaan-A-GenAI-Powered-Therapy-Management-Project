from sqlalchemy import Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime


class TherapySession(Base):
    """Represents a therapy session transcript logged by the therapist."""
    __tablename__ = "therapy_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    session_date: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO date e.g. "2026-03-09"
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)   # auto-incremented per patient
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    therapist_notes: Mapped[str] = mapped_column(Text, nullable=True)      # private therapist notes (not shown to patient)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
