# app/education/erp/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import get_current_therapist, get_current_patient
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.education.erp.schemas import ERPEducation
from app.education.erp.service import generate_education
from app.education.erp.models import ERPEducationCache

router = APIRouter(prefix="/education/erp", tags=["education"])


# ── Patient endpoints ──────────────────────────────────────────────────────────

@router.get("/patient/my-education", response_model=ERPEducation)
async def get_patient_education(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """Return cached ERP education for the current patient (404 if not generated yet)."""
    cached = db.query(ERPEducationCache).filter(
        ERPEducationCache.patient_id == current_patient.id
    ).first()

    if not cached:
        raise HTTPException(
            status_code=404,
            detail="No education generated yet. Please generate education first.",
        )

    return ERPEducation(
        module="erp_education",
        topic=cached.topic,
        reading_level=cached.reading_level,
        sections=cached.sections_json,
        sources=cached.sources_json,
        disclaimer=cached.disclaimer,
    )


@router.post("/patient/generate", response_model=ERPEducation)
async def generate_patient_education(
    regenerate: bool = False,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """
    Generate (or return cached) ERP education for the current patient.
    Pass ?regenerate=true to force regeneration.
    """
    cached = db.query(ERPEducationCache).filter(
        ERPEducationCache.patient_id == current_patient.id
    ).first()

    if not regenerate and cached:
        return ERPEducation(
            module="erp_education",
            topic=cached.topic,
            reading_level=cached.reading_level,
            sections=cached.sections_json,
            sources=cached.sources_json,
            disclaimer=cached.disclaimer,
        )

    try:
        payload = generate_education(current_patient.therapist_id)
        education = ERPEducation.model_validate(payload)

        if cached:
            cached.topic = education.topic
            cached.reading_level = education.reading_level
            cached.sections_json = [s.model_dump() for s in education.sections]
            cached.sources_json = [s.model_dump() for s in education.sources]
            cached.disclaimer = education.disclaimer
        else:
            cached = ERPEducationCache(
                patient_id=current_patient.id,
                topic=education.topic,
                reading_level=education.reading_level,
                sections_json=[s.model_dump() for s in education.sections],
                sources_json=[s.model_dump() for s in education.sources],
                disclaimer=education.disclaimer,
            )
            db.add(cached)

        db.commit()
        db.refresh(cached)
        return education

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate education: {str(e)}",
        )


# ── Therapist endpoint (preview) ───────────────────────────────────────────────

@router.get("/therapist/preview", response_model=ERPEducation)
def therapist_preview_education(
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """Generate a preview of ERP education for the therapist (not cached)."""
    payload = generate_education(current_therapist.id)
    return ERPEducation.model_validate(payload)
