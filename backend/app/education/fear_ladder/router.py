# app/education/fear_ladder/router.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import get_current_therapist, get_current_patient
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.education.fear_ladder.schemas import FearLadderEducation
from app.education.fear_ladder.service import generate_education
from app.education.fear_ladder.models import FearLadderEducationCache

router = APIRouter(prefix="/education/fear-ladder", tags=["education"])


# Patient endpoints
@router.get("/patient/my-education", response_model=FearLadderEducation)
async def get_patient_education(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Get cached education for the current patient.
    Returns the last generated education if available.
    """
    cached = db.query(FearLadderEducationCache).filter(
        FearLadderEducationCache.patient_id == current_patient.id
    ).first()
    
    if not cached:
        raise HTTPException(
            status_code=404, 
            detail="No education generated yet. Please generate education first."
        )
    
    # Reconstruct FearLadderEducation from cached data
    return FearLadderEducation(
        module="fear_ladder_education",
        topic=cached.topic,
        reading_level=cached.reading_level,
        sections=cached.sections_json,
        sources=cached.sources_json,
        disclaimer=cached.disclaimer
    )


@router.post("/patient/generate", response_model=FearLadderEducation)
async def generate_patient_education(
    regenerate: bool = False,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Generate or regenerate education for the current patient.
    If regenerate=False and education exists, returns cached version.
    If regenerate=True, generates new education and updates cache.
    """
    # Check for existing cached education
    cached = db.query(FearLadderEducationCache).filter(
        FearLadderEducationCache.patient_id == current_patient.id
    ).first()
    
    # If not regenerating and cache exists, return cached version
    if not regenerate and cached:
        return FearLadderEducation(
            module="fear_ladder_education",
            topic=cached.topic,
            reading_level=cached.reading_level,
            sections=cached.sections_json,
            sources=cached.sources_json,
            disclaimer=cached.disclaimer
        )
    
    # Generate new education (using therapist's knowledge base)
    try:
        payload = generate_education(
            current_patient.therapist_id, 
            topic="Fear ladder (exposure hierarchy) in ERP for OCD"
        )
        education = FearLadderEducation.model_validate(payload)
        
        # Save or update cache
        if cached:
            # Update existing cache
            cached.topic = education.topic
            cached.reading_level = education.reading_level
            cached.sections_json = [section.model_dump() for section in education.sections]
            cached.sources_json = [source.model_dump() for source in education.sources]
            cached.disclaimer = education.disclaimer
        else:
            # Create new cache
            cached = FearLadderEducationCache(
                patient_id=current_patient.id,
                topic=education.topic,
                reading_level=education.reading_level,
                sections_json=[section.model_dump() for section in education.sections],
                sources_json=[source.model_dump() for source in education.sources],
                disclaimer=education.disclaimer
            )
            db.add(cached)
        
        db.commit()
        db.refresh(cached)
        
        return education
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate education: {str(e)}"
        )


# Therapist endpoint (for preview/testing)
@router.get("/therapist/preview", response_model=FearLadderEducation)
def therapist_preview_education(
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Generate a preview of fear ladder education for therapist.
    This does not cache the result.
    """
    payload = generate_education(current_therapist.id)
    return FearLadderEducation.model_validate(payload)