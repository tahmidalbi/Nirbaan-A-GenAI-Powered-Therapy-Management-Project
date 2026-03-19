from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database.base import Base


class HomeworkStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    skipped = "skipped"


class PatientHomework(Base):
    __tablename__ = "patient_homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapy_sessions.id"), nullable=False, index=True)

    # Homework content (from AI analysis)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)

    # Week organization
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[HomeworkStatus] = mapped_column(
        SQLEnum(HomeworkStatus), default=HomeworkStatus.active, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Patient notes
    patient_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", backref="homeworks")
    session = relationship("TherapySession", backref="approved_homeworks")
    approver = relationship("Therapist", foreign_keys=[approved_by])
