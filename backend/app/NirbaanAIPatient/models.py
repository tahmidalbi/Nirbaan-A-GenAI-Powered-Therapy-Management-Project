from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

# Import related models so SQLAlchemy registers them
import app.patients.models  # noqa: F401


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class PsychoeducationChatThread(Base):
    __tablename__ = "psychoeducation_chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
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

    messages: Mapped[List["PsychoeducationChatMessage"]] = relationship(
        "PsychoeducationChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PsychoeducationChatMessage.created_at.asc()",
    )


class PsychoeducationChatMessage(Base):
    __tablename__ = "psychoeducation_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("psychoeducation_chat_threads.id", ondelete="CASCADE"),
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

    thread: Mapped["PsychoeducationChatThread"] = relationship(
        "PsychoeducationChatThread",
        back_populates="messages",
    )