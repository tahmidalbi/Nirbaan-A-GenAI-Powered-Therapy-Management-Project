"""
Script to create AI ladder review tables in the database
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# Import models to register them with Base
from app.fear_ladder.models import (
    FearLadder, 
    FearLadderItem, 
    AILadderReview, 
    AILadderSuggestion, 
    AILadderEvidence
)
from app.patients.models import Patient
from app.therapists.models import Therapist

def create_ai_ladder_review_tables():
    """Create AI ladder review tables"""
    print("Creating AI ladder review tables...")
    
    try:
        # Create tables
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ AI ladder review tables created successfully!")
        print("  - ai_ladder_reviews")
        print("  - ai_ladder_suggestions")
        print("  - ai_ladder_evidence")
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    create_ai_ladder_review_tables()
