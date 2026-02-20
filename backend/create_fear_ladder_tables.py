"""
Script to create fear ladder tables in the database
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# Import models to register them with Base
from app.fear_ladder.models import FearLadder, FearLadderItem
from app.patients.models import Patient
from app.therapists.models import Therapist

def create_fear_ladder_tables():
    """Create fear ladder tables"""
    print("Creating fear ladder tables...")
    
    try:
        # Create tables
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ Fear ladder tables created successfully!")
        print("  - fear_ladders")
        print("  - fear_ladder_items")
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    create_fear_ladder_tables()
