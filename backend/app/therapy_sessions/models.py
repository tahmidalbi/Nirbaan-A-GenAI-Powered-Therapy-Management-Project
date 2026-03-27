from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime


class TherapySession(Base):
    """Unified therapy session supporting both real-time videocall and manual logging."""
    __tablename__ = "therapy_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)

    # Videocall fields
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Manual logging fields
    session_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ISO date e.g. "2026-03-09"
    session_number: Mapped[int | None] = mapped_column(Integer, nullable=True)   # auto-incremented per patient
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full transcript (manual or auto-generated)
    therapist_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    transcripts: Mapped[list["TherapyTranscript"]] = relationship("TherapyTranscript", back_populates="session", cascade="all, delete-orphan")
    analysis: Mapped["TherapySessionAnalysis | None"] = relationship(
        "TherapySessionAnalysis", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class TherapyTranscript(Base):
    """Granular transcript entries for real-time videocall sessions."""
    __tablename__ = "therapy_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapy_sessions.id"), nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)  # "therapist" or "patient"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    session: Mapped["TherapySession"] = relationship("TherapySession", back_populates="transcripts")


class TherapySessionAnalysis(Base):
    """AI-generated analysis for therapy sessions."""
    __tablename__ = "therapy_session_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("therapy_sessions.id"), nullable=False, unique=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    therapist_interventions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    patient_emotions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    homeworks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    session: Mapped["TherapySession"] = relationship("TherapySession", back_populates="analysis")
