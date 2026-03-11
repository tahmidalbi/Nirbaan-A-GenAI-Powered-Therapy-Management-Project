from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime
from typing import Optional


class ChatGroup(Base):
    __tablename__ = "chat_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    members: Mapped[list["ChatGroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatGroupMember(Base):
    __tablename__ = "chat_group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_groups.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    group: Mapped["ChatGroup"] = relationship(back_populates="members")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_groups.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)  # "therapist" or "patient"
    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    group: Mapped["ChatGroup"] = relationship(back_populates="messages")


class EPDirectMessage(Base):
    """Direct messages between a therapist and an emergency personnel member."""
    __tablename__ = "ep_direct_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ep_id: Mapped[int] = mapped_column(Integer, ForeignKey("emergency_personnel.id"), nullable=False)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(30), nullable=False)  # "therapist" | "emergency_personnel"
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EPGroup(Base):
    """One shared group chat per therapist — contains all their human helpers."""
    __tablename__ = "ep_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list["EPGroupMessage"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="EPGroupMessage.created_at"
    )


class EPGroupMessage(Base):
    """Message in an EP group chat. May be from therapist, EP, system, or AI agent."""
    __tablename__ = "ep_group_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("ep_groups.id"), nullable=False)
    sender_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # therapist | emergency_personnel | system | ai_agent
    sender_role: Mapped[str] = mapped_column(String(30), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional patient reference (used by AI agent alerts)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Claim: an EP marks "I am visiting this patient"
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claimed_by_ep_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    claimed_by_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    group: Mapped["EPGroup"] = relationship(back_populates="messages")
