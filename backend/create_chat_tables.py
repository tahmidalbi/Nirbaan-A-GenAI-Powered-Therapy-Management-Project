"""
Run this script once to create the chat tables:
    python create_chat_tables.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.session import engine
from app.database.base import Base

# Import all models so SQLAlchemy can resolve foreign key targets
import app.therapists.models   # noqa  (therapists table)
import app.patients.models     # noqa  (patients table)
import app.chat.models         # noqa  (chat tables)

if __name__ == "__main__":
    print("Creating chat tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Done! Tables created: chat_groups, chat_group_members, chat_messages")
