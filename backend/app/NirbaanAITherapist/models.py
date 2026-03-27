from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

# Ensure related models are registered
import app.patients.models  # noqa: F401


class TherapistChatRole(str, Enum):
    THERAPIST = "therapist"
    ASSISTANT = "assistant"


class AnalysisRunStatus(str, Enum):
    RUNNING = "running"
    NEEDS_CLARIFICATION = "needs_clarification"
    COMPLETED = "completed"
    FAILED = "failed"


class ClarificationStatus(str, Enum):
    PENDING = "pending"
    ANSWERED = "answered"


# ------------------------------------------------------------------
# Therapist chat layer
# ------------------------------------------------------------------

class TherapistAIChatThread(Base):
    __tablename__ = "therapist_ai_chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    therapist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("therapists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    patient_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[List["TherapistAIChatMessage"]] = relationship(
        "TherapistAIChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TherapistAIChatMessage.created_at.asc()",
    )


class TherapistAIChatMessage(Base):
    __tablename__ = "therapist_ai_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("therapist_ai_chat_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    thread: Mapped["TherapistAIChatThread"] = relationship(
        "TherapistAIChatThread",
        back_populates="messages",
    )


# ------------------------------------------------------------------
# Internal analysis workflow layer
# ------------------------------------------------------------------

class PatientAnalysisRun(Base):
    __tablename__ = "patient_analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    therapist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("therapists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link back to therapist chat thread
    thread_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("therapist_ai_chat_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AnalysisRunStatus.RUNNING.value,
        index=True,
    )

    analysis_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    draft_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    clarifications: Mapped[List["PatientAnalysisClarification"]] = relationship(
        "PatientAnalysisClarification",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PatientAnalysisClarification.created_at.asc()",
    )


class PatientAnalysisClarification(Base):
    __tablename__ = "patient_analysis_clarifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    analysis_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ClarificationStatus.PENDING.value,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    analysis_run: Mapped["PatientAnalysisRun"] = relationship(
        "PatientAnalysisRun",
        back_populates="clarifications",
    )