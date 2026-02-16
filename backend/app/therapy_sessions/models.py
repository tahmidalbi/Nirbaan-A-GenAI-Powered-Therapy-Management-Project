from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime
from typing import Optional

class TherapySession(Base):
    __tablename__ = "therapy_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
