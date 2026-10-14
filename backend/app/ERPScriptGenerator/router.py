from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.utils import get_current_therapist, get_current_user
from app.database.deps import get_db
from app.patients.models import Patient
from app.therapists.models import Therapist
from .schemas import (
    StartImaginalRunRequest,
    ReviewImaginalRunRequest,
    ImaginalRunResponse,
    ResumeResult,
    ApprovedImaginalScriptItem,
)
from .repository import (
    get_run_by_thread_id,
    list_approved_for_patient,
    get_approved_by_id,
    list_approved_for_erp_item,
)
from .service import start_run, resume_run, ai_revisions_remaining

router = APIRouter(prefix="/imaginal-generator", tags=["Imaginal Exposure Generator"])


def get_graph(request: Request):
    graph = getattr(request.app.state, "imaginal_graph", None)
    if graph is None:
        raise HTTPException(status_code=500, detail="Imaginal graph is not initialized")
    return graph


def _ensure_own_patient(db: Session, therapist: Therapist, patient_id: int) -> None:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or patient.therapist_id != therapist.id:
        raise HTTPException(status_code=403, detail="Patient is not in your workspace")


def _ensure_patient_access(db: Session, user, patient_id: int) -> None:
    if isinstance(user, Patient):
        if user.id != patient_id:
            raise HTTPException(status_code=403, detail="Not allowed")
    elif isinstance(user, Therapist):
        _ensure_own_patient(db, user, patient_id)
    else:
        raise HTTPException(status_code=403, detail="Not allowed")


@router.post("/start", response_model=ImaginalRunResponse)
def start_imaginal_generation(
    payload: StartImaginalRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    therapist: Therapist = Depends(get_current_therapist),
):
    _ensure_own_patient(db, therapist, payload.patient_id)
    payload.therapist_id = therapist.id

    graph = get_graph(request)
    config = start_run(graph, payload)

    thread_id = config["configurable"]["thread_id"]
    run = get_run_by_thread_id(db, thread_id)
    if not run:
        raise HTTPException(status_code=500, detail="Run was not created")

    return ImaginalRunResponse(
        thread_id=thread_id,
        run_id=run.id,
        status=run.status,
        version_no=run.revision_count,
        script_text=run.latest_script_text or "",
        interrupt_required=True,
        ai_revisions_remaining=ai_revisions_remaining(run.revision_count),
    )


@router.post("/review", response_model=ResumeResult)
def review_imaginal_generation(
    payload: ReviewImaginalRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    therapist: Therapist = Depends(get_current_therapist),
):
    graph = get_graph(request)

    run = get_run_by_thread_id(db, payload.thread_id)
    if not run or run.therapist_id != therapist.id:
        raise HTTPException(status_code=404, detail="Run not found")

    resume_run(graph, payload)

    # Expire the identity-map cache so the next query hits the DB and sees
    # the mutations committed by the graph nodes (which use separate sessions).
    db.expire_all()
    refreshed = get_run_by_thread_id(db, payload.thread_id)
    if not refreshed:
        raise HTTPException(status_code=404, detail="Run not found after resume")

    if refreshed.status == "approved":
        return ResumeResult(
            thread_id=payload.thread_id,
            run_id=refreshed.id,
            status=refreshed.status,
            version_no=refreshed.revision_count,
            script_text=refreshed.approved_script_text,
            interrupt_required=False,
            audio_path=refreshed.approved_audio_path,
            approved_script_id=refreshed.approved_script_id,
        )

    return ResumeResult(
        thread_id=payload.thread_id,
        run_id=refreshed.id,
        status=refreshed.status,
        version_no=refreshed.revision_count,
        script_text=refreshed.latest_script_text,
        interrupt_required=True,
        ai_revisions_remaining=ai_revisions_remaining(refreshed.revision_count),
    )


@router.get("/patient/{patient_id}/approved", response_model=list[ApprovedImaginalScriptItem])
def list_patient_approved_scripts(
    patient_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ensure_patient_access(db, user, patient_id)
    items = list_approved_for_patient(db, patient_id)
    return [
        ApprovedImaginalScriptItem(
            id=x.id,
            run_id=x.run_id,
            patient_id=x.patient_id,
            erp_item_id=x.erp_item_id,
            approved_script=x.approved_script,
            audio_path=x.audio_path,
            subtype=x.subtype,
            created_at=x.created_at,
        )
        for x in items
    ]


@router.get("/erp-item/{erp_item_id}/approved", response_model=list[ApprovedImaginalScriptItem])
def list_erp_item_approved_scripts(
    erp_item_id: int,
    db: Session = Depends(get_db),
    therapist: Therapist = Depends(get_current_therapist),
):
    items = [
        x for x in list_approved_for_erp_item(db, erp_item_id)
        if x.therapist_id == therapist.id
    ]
    return [
        ApprovedImaginalScriptItem(
            id=x.id,
            run_id=x.run_id,
            patient_id=x.patient_id,
            erp_item_id=x.erp_item_id,
            approved_script=x.approved_script,
            audio_path=x.audio_path,
            subtype=x.subtype,
            created_at=x.created_at,
        )
        for x in items
    ]


@router.get("/audio/{script_id}")
def stream_audio(
    script_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    script = get_approved_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    _ensure_patient_access(db, user, script.patient_id)

    # Streamed through the backend so the browser never needs direct R2 access.
    if script.audio_key:
        from .config import settings
        if settings.has_r2_config:
            from .r2_storage import open_object_stream
            body = open_object_stream(script.audio_key)
            return StreamingResponse(body.iter_chunks(), media_type="audio/wav")

    if script.audio_path and os.path.isfile(script.audio_path):
        return FileResponse(
            script.audio_path,
            media_type="audio/wav",
            filename=os.path.basename(script.audio_path),
        )

    raise HTTPException(status_code=404, detail="Audio file not available")