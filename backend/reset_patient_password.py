"""
Script to set a known password for a patient (for testing)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.patients.models import Patient
from app.auth.utils import get_password_hash
from app.core.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Get patient by email
    email = input("Enter patient email: ").strip()
    patient = db.query(Patient).filter(Patient.email == email).first()
    
    if not patient:
        print(f"\n❌ No patient found with email: {email}")
    else:
        print(f"\n✓ Found patient: {patient.name} ({patient.email})")
        new_password = input("Enter new password (min 8 characters): ").strip()
        
        if len(new_password) < 8:
            print("❌ Password must be at least 8 characters")
        else:
            # Hash and update password
            patient.hashed_password = get_password_hash(new_password)
            db.commit()
            print(f"\n✅ Password updated successfully for {patient.name}!")
            print(f"   Email: {patient.email}")
            print(f"   New Password: {new_password}")
            print(f"\nYou can now login with these credentials.")
            
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
