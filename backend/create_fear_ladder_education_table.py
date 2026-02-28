"""
Create fear_ladder_education_cache table for storing AI-generated education content.

This table caches the generated education for each patient, allowing them to see
their previously generated content when they log back in.

Run this script with:
    python backend/create_fear_ladder_education_table.py
"""
from sqlalchemy import create_engine, MetaData
from app.core.config import settings
from app.database.base import Base

# Import all models to ensure they're registered with Base.metadata
from app.patients.models import Patient  # Must import before FearLadderEducationCache
from app.education.fear_ladder.models import FearLadderEducationCache

def create_tables():
    """Create the fear_ladder_education_cache table"""
    engine = create_engine(settings.DATABASE_URL)
    
    print("Creating fear_ladder_education_cache table...")
    
    try:
        # Check if patients table exists, create if needed
        print("Ensuring patients table exists...")
        Base.metadata.create_all(
            bind=engine,
            tables=[Patient.__table__],
            checkfirst=True
        )
        
        # Now create the FearLadderEducationCache table
        print("Creating fear_ladder_education_cache table...")
        Base.metadata.create_all(
            bind=engine,
            tables=[FearLadderEducationCache.__table__],
            checkfirst=True
        )
        print("✓ Successfully created fear_ladder_education_cache table")
        
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    create_tables()
