"""
Create Progress Tracking Tables
This script creates the patient_progress and therapist_notes tables
Run this after running create_tables.py to add progress tracking functionality
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.database.session import engine
from app.database.base import Base
from app.progress.models import PatientProgress, TherapistNote
from app.patients.models import Patient
from app.therapists.models import Therapist

def create_progress_tables():
    """Create progress tracking tables"""
    try:
        print("Creating progress tracking tables...")
        
        # Import all models to ensure they're registered
        print("Imported models:")
        print(f"  - PatientProgress: {PatientProgress.__tablename__}")
        print(f"  - TherapistNote: {TherapistNote.__tablename__}")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        print("\n✓ Progress tracking tables created successfully!")
        print("\nTables created:")
        print("  - patient_progress")
        print("  - therapist_notes")
        
    except Exception as e:
        print(f"\n✗ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_progress_tables()
