from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime

class PatientProgress(Base):
    __tablename__ = "patient_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    initial_condition: Mapped[str] = mapped_column(Text, nullable=True)  # Initial detailed condition description
    weekly_progress: Mapped[dict] = mapped_column(JSON, nullable=True, default={})  # {"week_1": "progress text", "week_2": "..."}
    current_week: Mapped[int] = mapped_column(Integer, default=0)  # Track current week number
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TherapistNote(Base):
    __tablename__ = "therapist_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    week_notes: Mapped[dict] = mapped_column(JSON, nullable=True, default={})  # {"initial": "note", "week_1": "note", "week_2": "note"}
    ai_protocol_instruction: Mapped[str] = mapped_column(Text, nullable=True)  # How therapist wants AI to suggest protocol
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
