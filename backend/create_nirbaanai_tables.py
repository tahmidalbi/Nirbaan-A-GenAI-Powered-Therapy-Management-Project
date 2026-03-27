"""
Script to create NirbaanAI psychoeducation chat tables in the database.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine
from app.database.base import Base

# Import models so SQLAlchemy registers them
from app.patients.models import Patient          # noqa: F401
from app.NirbaanAIPatient.models import (        # noqa: F401
    PsychoeducationChatThread,
    PsychoeducationChatMessage,
)


def create_tables():
    print("Creating NirbaanAI chat tables...")
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ Tables created successfully!")
        print("  - psychoeducation_chat_threads")
        print("  - psychoeducation_chat_messages")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    create_tables()
