"""
Creates the therapy_sessions, therapy_transcripts, and therapy_session_analysis tables.
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
from app.therapy_sessions.models import TherapySession, TherapyTranscript, TherapySessionAnalysis  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(
        bind=engine,
        tables=[
            TherapySession.__table__,
            TherapyTranscript.__table__,
            TherapySessionAnalysis.__table__,
        ],
    )
    print("✅ therapy_sessions, therapy_transcripts, therapy_session_analysis tables created successfully.")
