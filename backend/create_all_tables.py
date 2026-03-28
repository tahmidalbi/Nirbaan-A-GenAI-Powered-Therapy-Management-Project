"""
Complete database setup script
Creates all tables including the new patient_intakes table
"""
from app.database.session import engine
from app.database.base import Base

# Import all models to ensure they're registered
from app.users.models import User
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.emergency_personnel.models import EmergencyPersonnel
from app.resources.models import Resource, IngestionJob
from app.intakes.models import PatientIntake
from app.erp.models import (                     # noqa: F401
    ERPItem,
    ERPImaginalCard,
    ERPLiveSession,
    ERPSUDSReading,
    ERPExerciseNote,
    ERPChatMessage,
)

def create_all_tables():
    """Create all database tables"""
    print("Creating all database tables...")
    print("\nTables to be created:")
    print("  1. users")
    print("  2. therapists")
    print("  3. patients")
    print("  4. emergency_personnel")
    print("  5. resources")
    print("  6. ingestion_jobs")
    print("  7. patient_intakes")
    print("  8. erp_items")
    print("  9. erp_imaginal_cards")
    print("  10. erp_live_sessions")
    print("  11. erp_suds_readings")
    print("  12. erp_exercise_notes")
    print("  13. erp_chat_messages")

    Base.metadata.create_all(bind=engine)

    print("\nAll tables created successfully!")

if __name__ == "__main__":
    create_all_tables()
