"""
Script to create ERP workspace tables in the database.
Run from the backend/ directory:
    python create_erp_tables.py
"""
from __future__ import annotations

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# Import all models that the ERP model depends on so they are registered
from app.patients.models import Patient          # noqa: F401 (registers "patients" table)
from app.erp.models import (                     # noqa: F401
    ERPItem,
    ERPImaginalCard,
    ERPLiveSession,
    ERPSUDSReading,
    ERPExerciseNote,
    ERPChatMessage,
)


def create_erp_tables() -> None:
    print("Creating ERP workspace tables...")
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ ERP tables created successfully!")
        print("  - erp_items")
        print("  - erp_imaginal_cards")
        print("  - erp_live_sessions")
        print("  - erp_suds_readings")
        print("  - erp_exercise_notes")
        print("  - erp_chat_messages")
    except Exception as exc:
        print(f"✗ Error creating tables: {exc}")
        raise


if __name__ == "__main__":
    create_erp_tables()
