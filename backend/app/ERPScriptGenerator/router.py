from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.deps import get_db
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
from .service import start_run, resume_run

router = APIRouter(prefix="/imaginal-generator", tags=["Imaginal Exposure Generator"])


def get_graph(request: Request):
    graph = getattr(request.app.state, "imaginal_graph", None)
    if graph is None:
        raise HTTPException(status_code=500, detail="Imaginal graph is not initialized")
    return graph


@router.post("/start", response_model=ImaginalRunResponse)
def start_imaginal_generation(
    payload: StartImaginalRunRequest,
    request: Request,
    db: Session = Depends(get_db),
):
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
    )


@router.post("/review", response_model=ResumeResult)
def review_imaginal_generation(
    payload: ReviewImaginalRunRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    graph = get_graph(request)

    run = get_run_by_thread_id(db, payload.thread_id)
    if not run:
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
    )


@router.get("/patient/{patient_id}/approved", response_model=list[ApprovedImaginalScriptItem])
def list_patient_approved_scripts(patient_id: int, db: Session = Depends(get_db)):
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
def list_erp_item_approved_scripts(erp_item_id: int, db: Session = Depends(get_db)):
    items = list_approved_for_erp_item(db, erp_item_id)
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
def stream_audio(script_id: int, db: Session = Depends(get_db)):
    """Serve approved-script audio — presigned R2 redirect or local file."""
    script = get_approved_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # If there's an R2 object key, generate a presigned URL and redirect
    if script.audio_key:
        from .config import settings
        if settings.has_r2_config:
            from .r2_storage import generate_presigned_download_url
            url = generate_presigned_download_url(script.audio_key)
            return RedirectResponse(url=url, status_code=307)

    # Fall back to local file
    if script.audio_path and os.path.isfile(script.audio_path):
        return FileResponse(
            script.audio_path,
            media_type="audio/wav",
            filename=os.path.basename(script.audio_path),
        )

    raise HTTPException(status_code=404, detail="Audio file not available")