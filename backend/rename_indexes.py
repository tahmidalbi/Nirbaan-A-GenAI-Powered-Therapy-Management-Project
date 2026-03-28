"""
After renaming therapy_sessions -> live_sessions, PostgreSQL kept the old index names.
This renames them so the new therapy_sessions table can create its own indexes.

Run: python rename_indexes.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import engine

INDEX_RENAMES = [
    ("ix_therapy_sessions_id",           "ix_live_sessions_id"),
    ("ix_therapy_sessions_patient_id",   "ix_live_sessions_patient_id"),
    ("ix_therapy_sessions_therapist_id", "ix_live_sessions_therapist_id"),
]

with engine.connect() as conn:
    for old_name, new_name in INDEX_RENAMES:
        exists = conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": old_name}
        ).scalar()

        if exists:
            conn.execute(text(f'ALTER INDEX {old_name} RENAME TO {new_name}'))
            print(f"[ok] Renamed index {old_name} -> {new_name}")
        else:
            print(f"[skip] {old_name} not found (already renamed or never existed)")

    conn.commit()
    print("\nDone.")
