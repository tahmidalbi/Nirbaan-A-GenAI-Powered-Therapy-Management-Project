"""
Creates the therapy_sessions table.
Run once: python create_therapy_sessions_table.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database.session import engine
from app.database.base import Base

# Import referenced models so SQLAlchemy can resolve foreign keys
from app.therapists.models import Therapist  # noqa: F401
from app.patients.models import Patient  # noqa: F401
from app.therapy_sessions.models import TherapySession  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine, tables=[TherapySession.__table__])
    print("✅ therapy_sessions table created successfully.")
