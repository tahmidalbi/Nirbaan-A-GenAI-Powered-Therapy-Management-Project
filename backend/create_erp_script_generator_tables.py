"""
Creates the three ERPScriptGenerator tables:
  - imaginal_script_runs
  - imaginal_script_versions
  - approved_imaginal_scripts

Run from the backend/ directory with the venv active:
    python create_erp_script_generator_tables.py
"""
from __future__ import annotations

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# ── dependency tables must be imported first so SQLAlchemy knows their PKs ──
from app.therapists.models import Therapist          # noqa: F401  → therapists
from app.patients.models import Patient              # noqa: F401  → patients
from app.erp.models import ERPItem                   # noqa: F401  → erp_items

# ── the three new tables ──
from app.ERPScriptGenerator.models import (          # noqa: F401
    ImaginalScriptRun,
    ImaginalScriptVersion,
    ApprovedImaginalScript,
)


def create_tables() -> None:
    print("Creating ERPScriptGenerator tables…")
    print("  • imaginal_script_runs")
    print("  • imaginal_script_versions")
    print("  • approved_imaginal_scripts")

    try:
        Base.metadata.create_all(
            bind=engine,
            tables=[
                ImaginalScriptRun.__table__,
                ImaginalScriptVersion.__table__,
                ApprovedImaginalScript.__table__,
            ],
        )
        print("\n✅ Tables created (or already exist).")
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        raise


if __name__ == "__main__":
    create_tables()
