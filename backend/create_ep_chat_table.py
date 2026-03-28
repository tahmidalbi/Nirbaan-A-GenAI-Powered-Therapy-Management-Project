"""
Creates the ep_direct_messages table for therapist <-> emergency personnel direct messaging.
Run once from the backend/ directory:
    .\venv\Scripts\python.exe create_ep_chat_table.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.base import Base
from app.database.session import engine

# Import all models so SQLAlchemy knows about their tables
import app.therapists.models          # noqa
import app.patients.models            # noqa
import app.emergency_personnel.models # noqa
import app.chat.models                # noqa  <- includes EPDirectMessage

def main():
    print("Creating ep_direct_messages table …")
    Base.metadata.create_all(bind=engine, tables=[
        Base.metadata.tables["ep_direct_messages"]
    ])
    print("Done ✓")

if __name__ == "__main__":
    main()
