"""
Test script to check therapist login functionality
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.therapists.models import Therapist
from app.auth.utils import verify_password
from app.core.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Get all therapists
    therapists = db.query(Therapist).all()
    
    print(f"\n{'='*60}")
    print(f"Total therapists in database: {len(therapists)}")
    print(f"{'='*60}\n")
    
    for therapist in therapists:
        print(f"ID: {therapist.id}")
        print(f"Name: {therapist.name}")
        print(f"Email: {therapist.email}")
        print(f"License: {therapist.license_number}")
        print(f"Specialty: {therapist.specialty}")
        print(f"Hashed Password (first 50 chars): {therapist.hashed_password[:50]}...")
        print(f"Password starts with $2b$: {therapist.hashed_password.startswith('$2b$')}")
        print(f"Password length: {len(therapist.hashed_password)}")
        print(f"Created: {therapist.created_at}")
        print(f"{'-'*60}\n")
        
        # Test password verification with common test passwords
        test_passwords = ['password123', 'test12345', 'testpass123', 'password', '12345678']
        print("Testing common passwords:")
        for test_pass in test_passwords:
            result = verify_password(test_pass, therapist.hashed_password)
            if result:
                print(f"  ✓ '{test_pass}' - MATCHES!")
            else:
                print(f"  ✗ '{test_pass}' - no match")
        print(f"{'-'*60}\n")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
    print("\nTo test therapist login:")
    print("1. Note the email and actual password you used during registration")
    print("2. Try logging in with those exact credentials")
    print("3. Password is case-sensitive!\n")
