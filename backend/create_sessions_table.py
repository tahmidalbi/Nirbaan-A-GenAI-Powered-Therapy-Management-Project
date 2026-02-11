"""
Create therapy_sessions table
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import engine
from app.database.base import Base
from app.sessions.models import TherapySession
from app.patients.models import Patient
from app.therapists.models import Therapist

def create_sessions_table():
    """Create the therapy_sessions table"""
    print("\n" + "="*60)
    print("Creating therapy_sessions table...")
    print("="*60 + "\n")
    
    try:
        # Create tables
        Base.metadata.create_all(bind=engine, tables=[TherapySession.__table__])
        
        print("✅ Successfully created therapy_sessions table!")
        print("\nTable Structure:")
        print("  - id: Primary Key")
        print("  - patient_id: Foreign Key → patients.id")
        print("  - therapist_id: Foreign Key → therapists.id")
        print("  - week_number: Integer (Week 1, Week 2, etc.)")
        print("  - session_date: DateTime")
        print("  - transcript: Text (Session transcript)")
        print("  - created_at: DateTime")
        print("  - updated_at: DateTime")
        print("\n" + "="*60)
        print("Database is ready for session transcripts!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error creating table: {str(e)}")
        raise

if __name__ == "__main__":
    create_sessions_table()
