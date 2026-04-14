from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime

class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_to_active_session: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # Relationships
    transcripts: Mapped[list["LiveSessionTranscript"]] = relationship("LiveSessionTranscript", back_populates="session")
    analysis: Mapped["LiveSessionAnalysis | None"] = relationship(
        "LiveSessionAnalysis", back_populates="session", uselist=False
    )


class LiveSessionTranscript(Base):
    __tablename__ = "live_session_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("live_sessions.id"), nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)  # "therapist" or "patient"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    session: Mapped["LiveSession"] = relationship("LiveSession", back_populates="transcripts")


class LiveSessionAnalysis(Base):
    __tablename__ = "live_session_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("live_sessions.id"), nullable=False, unique=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    therapist_interventions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    patient_emotions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    homeworks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    session: Mapped["LiveSession"] = relationship("LiveSession", back_populates="analysis")
