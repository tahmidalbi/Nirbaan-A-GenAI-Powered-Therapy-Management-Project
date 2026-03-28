"""
Create / migrate therapy session tables:
  - Adds 'confidence' column to live_session_transcripts (if missing)
  - Creates live_session_analysis table (if missing)
  - Adds 'patient_emotions' column to live_session_analysis (if missing)
  - Adds 'homeworks' column to live_session_analysis (if missing)

Run:  python create_session_analysis_table.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import engine

with engine.connect() as conn:
    # 1. Add confidence column to live_session_transcripts
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'live_session_transcripts' AND column_name = 'confidence'
    """))
    if result.fetchone() is None:
        conn.execute(text("ALTER TABLE live_session_transcripts ADD COLUMN confidence FLOAT"))
        print("✓ Added 'confidence' column to live_session_transcripts")
    else:
        print("• 'confidence' column already exists")

    # 2. Create live_session_analysis table
    result = conn.execute(text("""
        SELECT to_regclass('public.live_session_analysis')
    """))
    if result.scalar() is None:
        conn.execute(text("""
            CREATE TABLE live_session_analysis (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL UNIQUE REFERENCES live_sessions(id),
                summary TEXT NOT NULL,
                detected_topics JSONB NOT NULL DEFAULT '[]',
                therapist_interventions JSONB NOT NULL DEFAULT '[]',
                patient_emotions JSONB NOT NULL DEFAULT '[]',
                homeworks JSONB NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        print("✓ Created live_session_analysis table")
    else:
        print("• live_session_analysis table already exists")

    # 3. Add patient_emotions column if missing
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'live_session_analysis' AND column_name = 'patient_emotions'
    """))
    if result.fetchone() is None:
        conn.execute(text("ALTER TABLE live_session_analysis ADD COLUMN patient_emotions JSONB NOT NULL DEFAULT '[]'"))
        print("✓ Added 'patient_emotions' column to live_session_analysis")
    else:
        print("• 'patient_emotions' column already exists")

    # 4. Add homeworks column if missing
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'live_session_analysis' AND column_name = 'homeworks'
    """))
    if result.fetchone() is None:
        conn.execute(text("ALTER TABLE live_session_analysis ADD COLUMN homeworks JSONB NOT NULL DEFAULT '[]'"))
        print("✓ Added 'homeworks' column to live_session_analysis")
    else:
        print("• 'homeworks' column already exists")

    conn.commit()
    print("\nDone.")
