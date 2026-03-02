from __future__ import annotations

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, JSON, Float, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class ERPItem(Base):
    """Represents one OCD obsession item in a patient's ERP recovery plan."""

    __tablename__ = "erp_items"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    obsession = Column(Text, nullable=False)
    compulsions = Column(JSON, nullable=False, default=list)
    suds = Column(Integer, nullable=True)
    session_exercise_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", backref="erp_items")
    imaginal_cards = relationship(
        "ERPImaginalCard", back_populates="erp_item", cascade="all, delete-orphan",
        order_by="ERPImaginalCard.order_index",
    )
    live_sessions = relationship(
        "ERPLiveSession", back_populates="erp_item", cascade="all, delete-orphan",
        order_by="ERPLiveSession.created_at",
    )


class ERPImaginalCard(Base):
    """An imaginal exposure card attached to an ERP item."""

    __tablename__ = "erp_imaginal_cards"

    id = Column(Integer, primary_key=True, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    erp_item = relationship("ERPItem", back_populates="imaginal_cards")


class ERPLiveSession(Base):
    """
    A live ERP exposure session for one obsession item.

    Timer logic:
      - accumulated_seconds: total seconds elapsed in previous segments (before latest resume)
      - resumed_at: UTC timestamp of the last resume/start (null when paused/ended)
      - status: 'running' | 'paused' | 'ended'

    Client computes display time:
      if running  → accumulated_seconds + (now_unix - resumed_at_unix)
      if paused   → accumulated_seconds
    """

    __tablename__ = "erp_live_sessions"

    id = Column(Integer, primary_key=True, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    status = Column(String(10), nullable=False, default="running")   # running | paused | ended
    accumulated_seconds = Column(Float, nullable=False, default=0.0)
    resumed_at = Column(DateTime, nullable=True)   # null when paused / ended
    ended_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    erp_item = relationship("ERPItem", back_populates="live_sessions")
    patient = relationship("Patient")
    suds_readings = relationship(
        "ERPSUDSReading", back_populates="session", cascade="all, delete-orphan",
        order_by="ERPSUDSReading.recorded_at",
    )


class ERPSUDSReading(Base):
    """A single SUDS data-point recorded during a live session."""

    __tablename__ = "erp_suds_readings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("erp_live_sessions.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    suds_value = Column(Integer, nullable=False)           # 0-100
    elapsed_seconds = Column(Float, nullable=False, default=0.0)   # timer value at submission
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ERPLiveSession", back_populates="suds_readings")


class ERPExerciseNote(Base):
    """
    A prescribed exercise note the patient writes before/during a session.
    Each save creates a new record; the latest is shown to the patient.
    The therapist can review the full history.
    """

    __tablename__ = "erp_exercise_notes"

    id = Column(Integer, primary_key=True, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    erp_item = relationship("ERPItem", backref="exercise_notes")
    patient = relationship("Patient")

