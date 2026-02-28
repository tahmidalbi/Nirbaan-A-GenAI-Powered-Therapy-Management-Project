"""
Create self-monitoring tables.

Run this script once to create the necessary tables for self-monitoring feature.
"""

from app.database.session import engine
from app.database.base import Base

# Import all models to ensure they're registered with Base
from app.self_monitoring.models import SelfMonitoringDay, SelfMonitoringEntry
from app.patients.models import Patient
from app.therapists.models import Therapist


def create_self_monitoring_tables():
    """Create self-monitoring tables in the database."""
    print("Creating self-monitoring tables...")
    
    # This will create only tables that don't exist yet
    Base.metadata.create_all(bind=engine)
    
    print("Self-monitoring tables created successfully!")
    print("Tables created:")
    print("  - self_monitoring_days")
    print("  - self_monitoring_entries")


if __name__ == "__main__":
    create_self_monitoring_tables()
