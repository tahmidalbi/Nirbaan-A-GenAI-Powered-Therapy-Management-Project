"""
Rename therapy session tables to match new module names.

Old name                  -> New name
-----------------------------------------
therapy_sessions          -> live_sessions
therapy_transcripts       -> live_session_transcripts
therapy_session_analysis  -> live_session_analysis

Run: python rename_tables.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import engine

RENAMES = [
    ("therapy_sessions",         "live_sessions"),
    ("therapy_transcripts",      "live_session_transcripts"),
    ("therapy_session_analysis", "live_session_analysis"),
]

with engine.connect() as conn:
    for old_name, new_name in RENAMES:
        old_exists = conn.execute(text(f"SELECT to_regclass('public.{old_name}')")).scalar() is not None
        new_exists = conn.execute(text(f"SELECT to_regclass('public.{new_name}')")).scalar() is not None

        if new_exists:
            print(f"[skip] {new_name} already exists")
        elif old_exists:
            conn.execute(text(f'ALTER TABLE {old_name} RENAME TO {new_name}'))
            print(f"[ok] Renamed {old_name} -> {new_name}")
        else:
            print(f"[skip] Neither {old_name} nor {new_name} exists — will be created fresh")

    conn.commit()
    print("\nDone.")
