import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.utils import create_access_token
from app.database.base import Base
from app.database.deps import get_db
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.ERPScriptGenerator.config import settings
from app.ERPScriptGenerator.models import ApprovedImaginalScript, ImaginalScriptRun
from app.ERPScriptGenerator.router import router
from app.ERPScriptGenerator.service import ai_revisions_remaining

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
TABLES = [
    Therapist.__table__,
    Patient.__table__,
    ImaginalScriptRun.__table__,
    ApprovedImaginalScript.__table__,
]
AUDIO_BYTES = b"RIFF-test-audio"


def token(email: str, user_id: int, role: str) -> dict:
    jwt = create_access_token({"sub": email, "id": user_id, "role": role})
    return {"Authorization": f"Bearer {jwt}"}


THERAPIST_1 = token("t1@example.com", 1, "therapist")
THERAPIST_2 = token("t2@example.com", 2, "therapist")
PATIENT_1 = token("p1@example.com", 1, "patient")
PATIENT_2 = token("p2@example.com", 2, "patient")


@pytest.fixture
def client(tmp_path):
    Base.metadata.create_all(engine, tables=TABLES)
    audio_file = tmp_path / "script.wav"
    audio_file.write_bytes(AUDIO_BYTES)

    db = TestingSession()
    db.add_all([
        Therapist(id=1, name="T1", email="t1@example.com", hashed_password="x",
                  license_number="L1", specialty="OCD", address="A"),
        Therapist(id=2, name="T2", email="t2@example.com", hashed_password="x",
                  license_number="L2", specialty="OCD", address="A"),
    ])
    db.commit()
    db.add_all([
        Patient(id=1, name="P1", email="p1@example.com", hashed_password="x",
                conditions="OCD", address="A", therapist_id=1),
        Patient(id=2, name="P2", email="p2@example.com", hashed_password="x",
                conditions="OCD", address="A", therapist_id=2),
    ])
    db.commit()
    db.add(ImaginalScriptRun(
        id=1, thread_id="thread-1", patient_id=1, therapist_id=1, erp_item_id=1,
        obsession="o", compulsion="c", feared_consequence="f", script_intensity="5/10",
    ))
    db.commit()
    db.add(ApprovedImaginalScript(
        id=1, patient_id=1, therapist_id=1, erp_item_id=1, run_id=1,
        approved_script="Approved text", audio_path=str(audio_file),
    ))
    db.commit()
    db.close()

    app = FastAPI()
    app.include_router(router)
    app.state.imaginal_graph = object()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    Base.metadata.drop_all(engine, tables=TABLES)


# --- Audio ---

def test_unauthenticated_audio_is_denied(client):
    assert client.get("/imaginal-generator/audio/1").status_code == 401


def test_treating_therapist_can_play_audio(client):
    response = client.get("/imaginal-generator/audio/1", headers=THERAPIST_1)
    assert response.status_code == 200
    assert response.content == AUDIO_BYTES


def test_patient_can_play_own_audio(client):
    response = client.get("/imaginal-generator/audio/1", headers=PATIENT_1)
    assert response.status_code == 200
    assert response.content == AUDIO_BYTES


def test_other_patient_cannot_play_audio(client):
    assert client.get("/imaginal-generator/audio/1", headers=PATIENT_2).status_code == 403


def test_other_therapist_cannot_play_audio(client):
    assert client.get("/imaginal-generator/audio/1", headers=THERAPIST_2).status_code == 403


# --- Approved script lists ---

def test_unauthenticated_script_list_is_denied(client):
    assert client.get("/imaginal-generator/patient/1/approved").status_code == 401


def test_patient_can_list_own_scripts(client):
    response = client.get("/imaginal-generator/patient/1/approved", headers=PATIENT_1)
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == [1]


def test_other_patient_cannot_list_scripts(client):
    response = client.get("/imaginal-generator/patient/1/approved", headers=PATIENT_2)
    assert response.status_code == 403


def test_other_therapist_sees_no_scripts_for_item(client):
    response = client.get("/imaginal-generator/erp-item/1/approved", headers=THERAPIST_2)
    assert response.status_code == 200
    assert response.json() == []


# --- Approval gate ---

def test_patient_cannot_approve_script(client):
    response = client.post(
        "/imaginal-generator/review",
        json={"thread_id": "thread-1", "approved": True},
        headers=PATIENT_1,
    )
    assert response.status_code == 401


def test_other_therapist_cannot_approve_script(client):
    response = client.post(
        "/imaginal-generator/review",
        json={"thread_id": "thread-1", "approved": True},
        headers=THERAPIST_2,
    )
    assert response.status_code == 404


def test_therapist_cannot_start_run_for_other_patient(client):
    response = client.post(
        "/imaginal-generator/start",
        json={
            "patient_id": 2, "therapist_id": 1, "erp_item_id": 1,
            "feared_consequence": "feared outcome", "script_intensity": "5/10",
        },
        headers=THERAPIST_1,
    )
    assert response.status_code == 403


# --- AI revision limit ---

def test_ai_revisions_run_out_after_configured_maximum():
    limit = settings.IMAGINAL_MAX_AI_REVISIONS
    assert ai_revisions_remaining(1) == limit
    assert ai_revisions_remaining(limit + 1) == 0
    assert ai_revisions_remaining(limit + 5) == 0
