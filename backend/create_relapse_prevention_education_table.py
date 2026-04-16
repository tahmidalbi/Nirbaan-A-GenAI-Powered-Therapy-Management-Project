"""
Create relapse_prevention_education_cache table.

Run with:
    python backend/create_relapse_prevention_education_table.py
"""
from sqlalchemy import create_engine
from app.core.config import settings
from app.database.base import Base
from app.patients.models import Patient
from app.education.relapse_prevention.models import RelapsePreventionEducationCache


def create_tables():
    engine = create_engine(settings.DATABASE_URL)

    print("Ensuring patients table exists...")
    Base.metadata.create_all(bind=engine, tables=[Patient.__table__], checkfirst=True)

    print("Creating relapse_prevention_education_cache table...")
    Base.metadata.create_all(
        bind=engine,
        tables=[RelapsePreventionEducationCache.__table__],
        checkfirst=True,
    )
    print("✓ Done.")
    engine.dispose()


if __name__ == "__main__":
    create_tables()
