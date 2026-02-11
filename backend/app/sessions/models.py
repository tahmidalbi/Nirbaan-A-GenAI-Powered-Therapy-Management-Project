"""
Session Models - Video Session Transcripts
Stores therapy session transcripts (dummy data for now, will integrate with video pipeline later)
"""
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.base import Base


class TherapySession(Base):
    """
    Stores therapy session transcripts for patients
    - Each session belongs to a patient and therapist
    - Sessions are numbered (week_number)
    - Transcript field stores the session content (dummy for now)
    - Will be integrated with LangGraph pipeline later
    """
    __tablename__ = "therapy_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Week 1, Week 2, etc.
    session_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)  # Session transcript (dummy for now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="therapy_sessions")
    therapist: Mapped["Therapist"] = relationship("Therapist", backref="therapy_sessions")
