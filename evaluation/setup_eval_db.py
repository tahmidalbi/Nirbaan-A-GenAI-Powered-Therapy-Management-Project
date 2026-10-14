"""Create the separate evaluation database, all tables, and synthetic accounts.

Usage: python evaluation/setup_eval_db.py
"""
import os

import common

common.configure()

import psycopg  # noqa: E402


def ensure_database() -> None:
    admin_url = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (common.EVAL_DB,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{common.EVAL_DB}"')
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")


def seed_accounts() -> None:
    from app.database.session import SessionLocal
    from app.erp.models import ERPItem
    from app.patients.models import Patient
    from app.therapists.models import Therapist

    obsessions = {
        "A": ("Fear that I left the stove on and the house will burn down",
              ["Checking the stove repeatedly", "Asking family to confirm it is off"]),
        "B": ("Fear of contamination from door handles",
              ["Washing hands many times", "Avoiding public doors"]),
        "C": ("Intrusive thought that I might harm someone",
              ["Avoiding knives", "Seeking reassurance that I am a good person"]),
    }

    db = SessionLocal()
    try:
        for key, ws in common.WORKSPACES.items():
            therapist = db.query(Therapist).filter(Therapist.email == ws["therapist_email"]).first()
            if not therapist:
                therapist = Therapist(
                    name=f"Evaluation Therapist {key}", email=ws["therapist_email"],
                    hashed_password="not-used", license_number=f"EVAL-{key}",
                    specialty="OCD", address="Synthetic",
                )
                db.add(therapist)
                db.commit()
                db.refresh(therapist)

            patient = db.query(Patient).filter(Patient.email == ws["patient_email"]).first()
            if not patient:
                patient = Patient(
                    name=f"Evaluation Patient {key}", email=ws["patient_email"],
                    hashed_password="not-used", conditions="OCD", address="Synthetic",
                    therapist_id=therapist.id,
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

            if not db.query(ERPItem).filter(ERPItem.patient_id == patient.id).first():
                obsession, compulsions = obsessions[key]
                db.add(ERPItem(patient_id=patient.id, obsession=obsession, compulsions=compulsions))
                db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    ensure_database()

    import create_all_tables  # backend/create_all_tables.py

    common.quiet_sql()
    create_all_tables.create_all_tables()
    seed_accounts()
    print("Evaluation database ready:", common.EVAL_DB, common.ids_by_workspace())
