"""
Migration: create patient_invitations table.
Run once: python add_patient_invitations_table.py
"""
from app.database.session import engine
from app.database.base import Base
from app.patients.invitation_model import PatientInvitation  # noqa: F401 – registers model

Base.metadata.create_all(bind=engine, tables=[PatientInvitation.__table__])
print("patient_invitations table created (or already exists).")
