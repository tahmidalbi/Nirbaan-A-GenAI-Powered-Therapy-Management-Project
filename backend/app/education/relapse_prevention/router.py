# app/education/relapse_prevention/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import get_current_therapist, get_current_patient
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.education.relapse_prevention.schemas import RelapsePreventionEducation
from app.education.relapse_prevention.service import generate_education
from app.education.relapse_prevention.models import RelapsePreventionEducationCache

router = APIRouter(prefix="/education/relapse-prevention", tags=["education"])


# ─── Patient endpoints ────────────────────────────────────────────────────────

@router.get("/patient/my-education", response_model=RelapsePreventionEducation)
async def get_patient_education(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """Return cached relapse prevention education for the current patient."""
    cached = db.query(RelapsePreventionEducationCache).filter(
        RelapsePreventionEducationCache.patient_id == current_patient.id
    ).first()

    if not cached:
        raise HTTPException(
            status_code=404,
            detail="No education generated yet. Please generate education first.",
        )

    return RelapsePreventionEducation(
        module="relapse_prevention_education",
        topic=cached.topic,
        reading_level=cached.reading_level,
        sections=cached.sections_json,
        sources=cached.sources_json,
        disclaimer=cached.disclaimer,
    )


@router.post("/patient/generate", response_model=RelapsePreventionEducation)
async def generate_patient_education(
    regenerate: bool = False,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """
    Generate or return cached relapse prevention education for the current patient.
    Pass ?regenerate=true to force a fresh generation.
    """
    cached = db.query(RelapsePreventionEducationCache).filter(
        RelapsePreventionEducationCache.patient_id == current_patient.id
    ).first()

    if not regenerate and cached:
        return RelapsePreventionEducation(
            module="relapse_prevention_education",
            topic=cached.topic,
            reading_level=cached.reading_level,
            sections=cached.sections_json,
            sources=cached.sources_json,
            disclaimer=cached.disclaimer,
        )

    try:
        payload = generate_education(current_patient.therapist_id)
        education = RelapsePreventionEducation.model_validate(payload)

        if cached:
            cached.topic = education.topic
            cached.reading_level = education.reading_level
            cached.sections_json = [s.model_dump() for s in education.sections]
            cached.sources_json = [s.model_dump() for s in education.sources]
            cached.disclaimer = education.disclaimer
        else:
            cached = RelapsePreventionEducationCache(
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


# ─── Therapist preview endpoint ───────────────────────────────────────────────

@router.get("/therapist/preview", response_model=RelapsePreventionEducation)
def therapist_preview_education(
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """Generate a relapse prevention education preview for the therapist (not cached)."""
    payload = generate_education(current_therapist.id)
    return RelapsePreventionEducation.model_validate(payload)
