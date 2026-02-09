from app.database.session import engine
from app.database.base import Base

# Import all models to ensure they're registered
from app.users.models import User
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.emergency_personnel.models import EmergencyPersonnel
from app.resources.models import Resource, ResourceChunk, IngestionJob

def create_tables():
    """Create all tables including new RAG tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")
    print("Tables: resources, resource_chunks, ingestion_jobs")

if __name__ == "__main__":
    create_tables()