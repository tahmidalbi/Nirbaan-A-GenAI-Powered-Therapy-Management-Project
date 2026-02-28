"""
Create ocd_core_education_cache table.

Run with:
    python backend/create_ocd_core_education_table.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from app.core.config import settings
from app.database.base import Base

# Import models to register them with Base.metadata
from app.patients.models import Patient          # noqa: F401
from app.therapists.models import Therapist      # noqa: F401
from app.education.ocd_core.models import OCDCoreEducationCache  # noqa: F401


def create_table():
    engine = create_engine(settings.DATABASE_URL)

    print("Creating ocd_core_education_cache table...")
    try:
        Base.metadata.create_all(
            bind=engine,
            tables=[OCDCoreEducationCache.__table__],
            checkfirst=True,
        )
        print("✓ ocd_core_education_cache table created (or already exists)")
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        raise


if __name__ == "__main__":
    create_table()
