"""
Create patient_homeworks table.

Run: python create_patient_homeworks_table.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import engine

with engine.connect() as conn:
    # Check if enum type exists
    result = conn.execute(text("""
        SELECT typname FROM pg_type WHERE typname = 'homeworkstatus'
    """))
    if result.fetchone() is None:
        conn.execute(text("""
            CREATE TYPE homeworkstatus AS ENUM ('active', 'completed', 'skipped')
        """))
        print("✓ Created homeworkstatus enum type")
    else:
        print("• homeworkstatus enum already exists")

    # Check if table exists
    result = conn.execute(text("""
        SELECT to_regclass('public.patient_homeworks')
    """))
    if result.scalar() is None:
        conn.execute(text("""
            CREATE TABLE patient_homeworks (
                id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                session_id INTEGER NOT NULL REFERENCES therapy_sessions(id),
                task TEXT NOT NULL,
                rationale TEXT NOT NULL,
                frequency VARCHAR(100) NOT NULL,
                week_number INTEGER NOT NULL,
                status homeworkstatus NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                approved_at TIMESTAMP,
                approved_by INTEGER REFERENCES therapists(id),
                completed_at TIMESTAMP,
                patient_notes TEXT
            )
        """))
        conn.execute(text("""
            CREATE INDEX idx_patient_homeworks_patient_id ON patient_homeworks(patient_id)
        """))
        conn.execute(text("""
            CREATE INDEX idx_patient_homeworks_session_id ON patient_homeworks(session_id)
        """))
        print("✓ Created patient_homeworks table")
    else:
        print("• patient_homeworks table already exists")

    conn.commit()
    print("\nDone.")
