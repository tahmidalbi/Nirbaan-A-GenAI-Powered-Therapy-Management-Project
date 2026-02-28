# app/education/ocd_core/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.education.ocd_core.models import OCDCoreEducationCache, OCDCoreEducationStatus
from app.education.ocd_core.schemas import OCDCoreEducation, Section, Source
from app.education.ocd_core.service import DEFAULT_TOPIC

router = APIRouter(prefix="/education/ocd-core", tags=["education-ocd-core"])


# ---------- Response models ----------

class OCDEducationStatusResponse(BaseModel):
    status: str
    error_message: Optional[str] = None
    education: Optional[OCDCoreEducation] = None


class TriggerResponse(BaseModel):
    message: str
    status: str


# ---------- Helpers ----------

def _cache_to_response(record: OCDCoreEducationCache) -> OCDEducationStatusResponse:
    if record.status != OCDCoreEducationStatus.completed or not record.sections_json:
        return OCDEducationStatusResponse(
            status=record.status,
            error_message=record.error_message,
        )

    education = OCDCoreEducation(
        module="ocd_core_education",
        topic=record.topic or DEFAULT_TOPIC,
        reading_level=record.reading_level or "simple",
        sections=[Section(**s) for s in (record.sections_json or [])],
        sources=[Source(**s) for s in (record.sources_json or [])],
        disclaimer=record.disclaimer or "",
    )
    return OCDEducationStatusResponse(
        status=record.status,
        education=education,
    )


# ---------- Patient Endpoints ----------

@router.get("/patient/my-education", response_model=OCDEducationStatusResponse)
async def get_patient_ocd_education(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """
    Get OCD core education for the current patient.
    Returns status + content if completed.
    Returns 404 if no generation has been triggered yet.
    """
    record = db.query(OCDCoreEducationCache).filter(
        OCDCoreEducationCache.patient_id == current_patient.id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="No OCD education generated yet. Please trigger generation first.",
        )

    return _cache_to_response(record)


@router.post("/patient/generate", response_model=TriggerResponse, status_code=202)
async def trigger_ocd_education_generation(
    regenerate: bool = False,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """
    Trigger async Celery generation of OCD core education.

    - If regenerate=False and status=completed: returns cached immediately.
    - If regenerate=False and status=queued|running: returns current status.
    - If regenerate=True or no record: fires a new Celery task.

    Returns 202 Accepted — the heavy generation happens in the background.
    """
    from app.education.ocd_core.tasks import generate_ocd_core_education_task

    record = db.query(OCDCoreEducationCache).filter(
        OCDCoreEducationCache.patient_id == current_patient.id
    ).first()

    # Return cached result if already completed and not forcing regeneration
    if not regenerate and record and record.status == OCDCoreEducationStatus.completed:
        return TriggerResponse(
            message="Education already generated.",
            status="completed",
        )

    # Don't queue again if one is already in-flight
    if not regenerate and record and record.status in (
        OCDCoreEducationStatus.queued,
        OCDCoreEducationStatus.running,
    ):
        return TriggerResponse(
            message="Generation already in progress.",
            status=record.status,
        )

    # Verify therapist is assigned
    patient = db.query(Patient).filter(Patient.id == current_patient.id).first()
    if not patient or not patient.therapist_id:
        raise HTTPException(
            status_code=400,
            detail="No therapist assigned to your account.",
        )

    # Create or reset the cache row to queued
    if record:
        record.status = OCDCoreEducationStatus.queued
        record.error_message = None
    else:
        record = OCDCoreEducationCache(
            patient_id=current_patient.id,
            status=OCDCoreEducationStatus.queued,
        )
        db.add(record)

    db.commit()

    # Fire Celery task
    generate_ocd_core_education_task.delay(
        patient_id=current_patient.id,
        therapist_id=patient.therapist_id,
        topic=DEFAULT_TOPIC,
    )

    return TriggerResponse(
        message="OCD education generation queued.",
        status="queued",
    )


# ---------- Therapist Endpoint ----------

@router.get("/therapist/preview/{patient_id}", response_model=OCDEducationStatusResponse)
async def therapist_view_patient_ocd_education(
    patient_id: int,
    current_therapist: Therapist = Depends(get_current_therapist),
    db: Session = Depends(get_db),
):
    """
    Therapist views the OCD core education for one of their patients.
    """
    # Verify patient belongs to this therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id,
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned to you.")

    record = db.query(OCDCoreEducationCache).filter(
        OCDCoreEducationCache.patient_id == patient_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="No OCD education generated for this patient yet.")

    return _cache_to_response(record)
