from app.database.session import engine
from app.database.base import Base

# Import all models to ensure they're registered (required for foreign keys)
from app.users.models import User
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.intakes.models import PatientIntake

def create_intakes_table():
    """Create patient intake table"""
    print("Creating intakes table...")
    Base.metadata.create_all(bind=engine)
    print("✅ patient_intakes table created successfully!")

if __name__ == "__main__":
    create_intakes_table()
