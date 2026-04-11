"""
Migration: add sent_to_active_session column to live_sessions.

Run once from the backend/ directory:
    python add_sent_to_active_session_column.py
"""
from __future__ import annotations

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.session import engine


def run() -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'live_sessions' "
                "AND column_name = 'sent_to_active_session'"
            )
        ).fetchone()

        if row:
            print("Column 'sent_to_active_session' already exists — nothing to do.")
        else:
            conn.execute(
                text(
                    "ALTER TABLE live_sessions "
                    "ADD COLUMN sent_to_active_session BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            conn.commit()
            print("Column 'sent_to_active_session' added successfully.")


if __name__ == "__main__":
    run()
