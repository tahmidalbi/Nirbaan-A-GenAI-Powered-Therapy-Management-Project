"""Create erp_exercise_notes table."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import engine
from app.database.base import Base

# Import all models so SQLAlchemy knows about them
from app.patients.models import Patient          # noqa: F401
from app.erp.models import (                     # noqa: F401
    ERPItem,
    ERPImaginalCard,
    ERPLiveSession,
    ERPSUDSReading,
    ERPExerciseNote,
)

Base.metadata.create_all(bind=engine, checkfirst=True)
print("Migration done: erp_exercise_notes table created (if it didn't exist).")
