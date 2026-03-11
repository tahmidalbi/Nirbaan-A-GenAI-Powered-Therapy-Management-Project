"""
Migration: create ep_patient_sessions and ep_patient_messages tables.
Run once from the backend/ directory:
    python create_ep_patient_tables.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.session import engine
from app.database.base import Base

# Import ALL models so Base.metadata knows about all tables (including FK targets)
import app.auth  # noqa
from app.therapists.models import Therapist  # noqa
from app.patients.models import Patient  # noqa
from app.emergency_personnel.models import EmergencyPersonnel  # noqa
from app.chat.models import (  # noqa
    ChatGroup, ChatGroupMember, ChatMessage,
    EPDirectMessage, EPGroup, EPGroupMessage,
    EPPatientSession, EPPatientMessage,
)

def main():
    print("Creating ep_patient_sessions and ep_patient_messages tables…")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Done.")

if __name__ == "__main__":
    main()
