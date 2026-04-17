"""
Migration: create emergency_personnel table.
Run once from the backend/ directory:
    .\\venv\\Scripts\\python.exe create_emergency_personnel_table.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database.base import Base
from app.database.session import engine

# Import parent model first so FK reference (therapists.id) resolves
from app.users.models import User                                   # noqa: F401
from app.therapists.models import Therapist                         # noqa: F401
from app.emergency_personnel.models import EmergencyPersonnel       # noqa: F401


def main():
    print("Creating emergency_personnel table...")
    try:
        Base.metadata.create_all(
            bind=engine,
            tables=[EmergencyPersonnel.__table__],
            checkfirst=True,
        )
        print("✓ emergency_personnel table created successfully!")
        print("  Columns:")
        print("    - id (PK)")
        print("    - name")
        print("    - email (unique)")
        print("    - hashed_password")
        print("    - education")
        print("    - experience")
        print("    - details")
        print("    - address")
        print("    - therapist_id (FK -> therapists.id)")
        print("    - public_key_jwk")
        print("    - created_at")
        print("    - updated_at")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
