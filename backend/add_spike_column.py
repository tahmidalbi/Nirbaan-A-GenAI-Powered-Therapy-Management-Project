"""
Migration: add last_spike_notified_suds column to erp_live_sessions.

Run once from the backend/ directory:
    python add_spike_column.py
"""
from __future__ import annotations

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.session import engine


def run() -> None:
    with engine.connect() as conn:
        # Check via information_schema — never causes a transaction abort
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'erp_live_sessions' "
                "AND column_name = 'last_spike_notified_suds'"
            )
        ).fetchone()

        if row:
            print("Column 'last_spike_notified_suds' already exists — nothing to do.")
            return

        print("Adding column 'last_spike_notified_suds' to erp_live_sessions…")
        conn.execute(
            text("ALTER TABLE erp_live_sessions ADD COLUMN last_spike_notified_suds INTEGER NULL")
        )
        conn.commit()
        print("Done.")


if __name__ == "__main__":
    run()
