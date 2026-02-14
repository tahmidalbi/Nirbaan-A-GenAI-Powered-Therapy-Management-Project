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
from app.resources.models import Resource, ResourceChunk, IngestionJob
from app.intakes.models import PatientIntake

def create_all_tables():
    """Create all database tables"""
    print("Creating all database tables...")
    print("\nTables to be created:")
    print("  1. users")
    print("  2. therapists")
    print("  3. patients")
    print("  4. emergency_personnel")
    print("  5. resources")
    print("  6. resource_chunks")
    print("  7. ingestion_jobs")
    print("  8. patient_intakes (NEW)")
    
    Base.metadata.create_all(bind=engine)
    
    print("\n✅ All tables created successfully!")
    print("\nYour database is now up to date with 8 tables.")

if __name__ == "__main__":
    create_all_tables()
