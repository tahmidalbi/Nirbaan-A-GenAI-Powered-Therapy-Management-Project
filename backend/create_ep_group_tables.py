"""
Create ep_groups and ep_group_messages tables.
Run from the backend/ directory:
    python create_ep_group_tables.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.base import Base
from app.database.session import engine

# Import all parent models first so FK references resolve
from app.therapists.models import Therapist          # noqa: F401
from app.emergency_personnel.models import EmergencyPersonnel  # noqa: F401
from app.chat.models import (                        # noqa: F401
    ChatGroup,
    ChatGroupMember,
    ChatMessage,
    EPDirectMessage,
    EPGroup,
    EPGroupMessage,
)

Base.metadata.create_all(
    bind=engine,
    tables=[
        EPGroup.__table__,
        EPGroupMessage.__table__,
    ],
)
print("✓ ep_groups and ep_group_messages tables created.")
