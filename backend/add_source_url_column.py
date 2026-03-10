"""
Migration: add source_url column to resources table.

Run once from the backend/ directory:
    python add_source_url_column.py
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
                "WHERE table_name = 'resources' "
                "AND column_name = 'source_url'"
            )
        ).fetchone()

        if row:
            print("Column 'source_url' already exists — nothing to do.")
            return

        print("Adding column 'source_url' to resources…")
        conn.execute(
            text("ALTER TABLE resources ADD COLUMN source_url VARCHAR(2000) NULL")
        )
        conn.commit()
        print("Done.")


if __name__ == "__main__":
    run()
