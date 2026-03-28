"""
Script to create NirbaanAITherapist tables in the database:
  - therapist_ai_chat_threads
  - therapist_ai_chat_messages
  - patient_analysis_runs
  - patient_analysis_clarifications
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# Import all models so SQLAlchemy registers them before create_all
from app.therapists.models import Therapist          # noqa: F401
from app.patients.models import Patient              # noqa: F401
from app.NirbaanAITherapist.models import (          # noqa: F401
    TherapistAIChatThread,
    TherapistAIChatMessage,
    PatientAnalysisRun,
    PatientAnalysisClarification,
)


def create_tables():
    print("Creating NirbaanAITherapist tables...")
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ Tables created successfully!")
        print("  - therapist_ai_chat_threads")
        print("  - therapist_ai_chat_messages")
        print("  - patient_analysis_runs")
        print("  - patient_analysis_clarifications")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    create_tables()
