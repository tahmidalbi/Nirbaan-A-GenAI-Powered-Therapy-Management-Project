from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


def _default_token() -> str:
    return str(uuid.uuid4())


def _default_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=7)


class EPInvitation(Base):
    __tablename__ = "ep_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False, default=_default_token
    )
    therapist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("therapists.id"), nullable=False
    )
    invited_email: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_default_expiry
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
