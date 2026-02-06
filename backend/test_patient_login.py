"""
Test script to check patient login functionality
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.patients.models import Patient
from app.auth.utils import verify_password
from app.core.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Get all patients
    patients = db.query(Patient).all()
    
    print(f"\n{'='*60}")
    print(f"Total patients in database: {len(patients)}")
    print(f"{'='*60}\n")
    
    for patient in patients:
        print(f"ID: {patient.id}")
        print(f"Name: {patient.name}")
        print(f"Email: {patient.email}")
        print(f"Hashed Password (first 50 chars): {patient.hashed_password[:50]}...")
        print(f"Password starts with $2b$: {patient.hashed_password.startswith('$2b$')}")
        print(f"Password length: {len(patient.hashed_password)}")
        print(f"Therapist ID: {patient.therapist_id}")
        print(f"Created: {patient.created_at}")
        print(f"{'-'*60}\n")
        
        # Test password verification with common test passwords
        test_passwords = ['password123', 'test12345', 'testpass123', 'password', '12345678']
        print("Testing common passwords:")
        for test_pass in test_passwords:
            result = verify_password(test_pass, patient.hashed_password)
            if result:
                print(f"  ✓ '{test_pass}' - MATCHES!")
            else:
                print(f"  ✗ '{test_pass}' - no match")
        print(f"{'-'*60}\n")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
    print("\nTo test patient login:")
    print("1. Note the email and actual password you used during registration")
    print("2. Try logging in with those exact credentials")
    print("3. Password is case-sensitive!\n")
