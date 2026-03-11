from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from datetime import datetime


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
