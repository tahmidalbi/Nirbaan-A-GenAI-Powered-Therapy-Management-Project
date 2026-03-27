"""
Create weekly progress table.

Run this script once to create the necessary table for the weekly progress feature.
"""

from app.database.session import engine
from app.database.base import Base

# Import all models to ensure they're registered with Base
from app.progress.models import WeeklyProgress
from app.patients.models import Patient
from app.therapists.models import Therapist


def create_progress_table():
    """Create weekly_progress table in the database."""
    print("Creating weekly progress table...")

    # This will create only tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    print("Weekly progress table created successfully!")
    print("Tables created:")
    print("  - weekly_progress")


if __name__ == "__main__":
    create_progress_table()
