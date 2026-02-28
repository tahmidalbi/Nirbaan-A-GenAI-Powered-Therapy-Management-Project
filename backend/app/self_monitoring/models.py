from sqlalchemy import String, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime


class SelfMonitoringDay(Base):
    """Represents a day of self-monitoring for a patient."""
    __tablename__ = "self_monitoring_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to entries
    entries: Mapped[list["SelfMonitoringEntry"]] = relationship(
        "SelfMonitoringEntry", 
        back_populates="day",
        cascade="all, delete-orphan"
    )


class SelfMonitoringEntry(Base):
    """Represents a single self-monitoring entry within a day."""
    __tablename__ = "self_monitoring_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day_id: Mapped[int] = mapped_column(Integer, ForeignKey("self_monitoring_days.id"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO date string
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # HH:MM format
    event: Mapped[str] = mapped_column(String, nullable=False)
    ritual: Mapped[str] = mapped_column(String, nullable=False)
    time_spent: Mapped[float] = mapped_column(Float, nullable=False)  # minutes
    anxiety_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-10
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to day
    day: Mapped["SelfMonitoringDay"] = relationship("SelfMonitoringDay", back_populates="entries")
