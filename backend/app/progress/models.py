from sqlalchemy import Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime
from typing import Optional


class WeeklyProgress(Base):
    """Represents a patient's weekly progress update."""
    __tablename__ = "weekly_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start_date: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO date string
    detailed_progress: Mapped[str] = mapped_column(Text, nullable=False)
    homework_reflection: Mapped[str] = mapped_column(Text, nullable=False)
    # List of {item_id, item_text, suds} — snapshot only, does not modify the original ladder
    suds_snapshot: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
