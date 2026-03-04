from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    DateTime,
    JSON,
    Float,
    String,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ERPItem(Base):
    """Represents one OCD obsession item in a patient's ERP recovery plan."""

    __tablename__ = "erp_items"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    obsession = Column(Text, nullable=False)
    compulsions = Column(JSON, nullable=False, default=list)

    # (optional / legacy fields — you can keep or remove later)
    suds = Column(Integer, nullable=True)
    session_exercise_note = Column(Text, nullable=True)

    # ✅ Used to show "latest report" under this obsession item (therapist + patient views)
    latest_session_id = Column(
        Integer,
        ForeignKey("erp_live_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", backref="erp_items")

    imaginal_cards = relationship(
        "ERPImaginalCard",
        back_populates="erp_item",
        cascade="all, delete-orphan",
        order_by="ERPImaginalCard.order_index",
    )

    live_sessions = relationship(
        "ERPLiveSession",
        back_populates="erp_item",
        cascade="all, delete-orphan",
        order_by="ERPLiveSession.created_at",
        foreign_keys="ERPLiveSession.erp_item_id",
    )

    # Latest session relationship (separate FK)
    latest_session = relationship(
        "ERPLiveSession",
        foreign_keys=[latest_session_id],
        post_update=True,  # helps avoid circular dependency issues
    )

    exercise_notes = relationship(
        "ERPExerciseNote",
        back_populates="erp_item",
        cascade="all, delete-orphan",
        order_by="ERPExerciseNote.created_at",
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
      - status: 'running' | 'paused' | 'ending' | 'ended'

    Client computes display time:
      if running  → accumulated_seconds + (now_unix - resumed_at_unix)
      if paused   → accumulated_seconds
      if ending   → accumulated_seconds (timer stopped)
      if ended    → accumulated_seconds
    """

    __tablename__ = "erp_live_sessions"

    id = Column(Integer, primary_key=True, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    status = Column(String(10), nullable=False, default="running")  # running|paused|ending|ended
    accumulated_seconds = Column(Float, nullable=False, default=0.0)
    resumed_at = Column(DateTime, nullable=True)  # null when paused/ending/ended
    ended_at = Column(DateTime, nullable=True)

    # ✅ Check-in support (scheduler uses this)
    last_checkin_at = Column(DateTime, nullable=True)
    last_agent_run_at = Column(DateTime, nullable=True)
    last_suds_at = Column(DateTime, nullable=True)

    # ✅ End-session debrief + reports
    patient_debrief_text = Column(Text, nullable=True)

    # Strict JSON blocks (frontend friendly)
    therapist_report_json = Column(JSON, nullable=True)
    patient_feedback_json = Column(JSON, nullable=True)

    report_version = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    erp_item = relationship("ERPItem", back_populates="live_sessions", foreign_keys=[erp_item_id])
    patient = relationship("Patient")

    suds_readings = relationship(
        "ERPSUDSReading",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ERPSUDSReading.recorded_at",
    )

    # ✅ Chat continuity for coach + patient messages
    messages = relationship(
        "ERPChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ERPChatMessage.created_at",
    )


class ERPSUDSReading(Base):
    """A single SUDS data-point recorded during a live session."""

    __tablename__ = "erp_suds_readings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("erp_live_sessions.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    suds_value = Column(Integer, nullable=False)  # 0-100
    elapsed_seconds = Column(Float, nullable=False, default=0.0)  # timer value at submission
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

    erp_item = relationship("ERPItem", back_populates="exercise_notes")
    patient = relationship("Patient")


class ERPChatMessage(Base):
    """
    Stores the chat transcript within a single ERP session.
    Used for continuity (message-by-message) + end-session report generation.
    """

    __tablename__ = "erp_chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("erp_live_sessions.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    # "patient" | "coach" | "system"
    role = Column(String(10), nullable=False, index=True)

    content = Column(Text, nullable=False)

    # Optional fields for debugging + research
    intent = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ERPLiveSession", back_populates="messages")
    patient = relationship("Patient")
    erp_item = relationship("ERPItem")