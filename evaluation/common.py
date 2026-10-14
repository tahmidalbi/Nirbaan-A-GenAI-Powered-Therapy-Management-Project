"""Shared setup: point the backend at a separate evaluation database before any app import."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
EVAL_DIR = ROOT / "evaluation"
DATA_DIR = EVAL_DIR / "data"
RESULTS_DIR = EVAL_DIR / "results"
EVAL_DB = os.environ.get("NIRBAAN_EVAL_DB", "nirbaan_eval")
# Disposable pgvector container: docker run -d --name nirbaan-eval-db -e POSTGRES_PASSWORD=2021
#   -e POSTGRES_DB=nirbaan_eval -p 5433:5432 pgvector/pgvector:pg16
EVAL_PG_HOST = os.environ.get("NIRBAAN_EVAL_PG_HOST", "localhost:5433")

# Synthetic evaluation accounts, one per therapist workspace.
WORKSPACES = {
    "A": {"therapist_email": "eval_therapist_a@example.com", "patient_email": "eval_patient_a@example.com"},
    "B": {"therapist_email": "eval_therapist_b@example.com", "patient_email": "eval_patient_b@example.com"},
    "C": {"therapist_email": "eval_therapist_c@example.com", "patient_email": "eval_patient_c@example.com"},
}


def _swap_db(url: str) -> str:
    scheme_and_auth = url.split("@", 1)[0]
    return f"{scheme_and_auth}@{EVAL_PG_HOST}/{EVAL_DB}"


def configure() -> None:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
    os.environ["DATABASE_URL"] = _swap_db(os.environ["DATABASE_URL"])
    os.environ["PGVECTOR_CONNECTION"] = _swap_db(os.environ["PGVECTOR_CONNECTION"])
    os.environ["LANGGRAPH_CHECKPOINT_DB_URL"] = os.environ["DATABASE_URL"]
    # Keep benchmark traffic out of LangSmith and avoid tracing overhead in timings.
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def quiet_sql() -> None:
    from app.database.session import engine

    engine.echo = False


def ids_by_workspace() -> dict:
    from app.database.session import SessionLocal
    from app.patients.models import Patient
    from app.therapists.models import Therapist

    db = SessionLocal()
    try:
        out = {}
        for key, ws in WORKSPACES.items():
            therapist = db.query(Therapist).filter(Therapist.email == ws["therapist_email"]).one()
            patient = db.query(Patient).filter(Patient.email == ws["patient_email"]).one()
            out[key] = {"therapist_id": therapist.id, "patient_id": patient.id}
        return out
    finally:
        db.close()
