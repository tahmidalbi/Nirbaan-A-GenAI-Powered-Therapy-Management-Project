"""One-shot migration: creates the ep_invitations table."""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.database.base import Base
from app.database.session import engine
from app.emergency_personnel.invitation_model import EPInvitation  # noqa: F401 — registers table

Base.metadata.create_all(bind=engine, tables=[EPInvitation.__table__])
print("ep_invitations table created (or already exists).")
