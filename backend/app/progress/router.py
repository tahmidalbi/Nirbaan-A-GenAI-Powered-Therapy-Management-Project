from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import datetime
from app.database.deps import get_db
from app.progress import models, schemas
from app.patients.models import Patient
from app.auth.utils import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])

# Patient endpoints
@router.post("/initial-condition", response_model=schemas.PatientProgressResponse)
def create_initial_condition(
    data: schemas.InitialConditionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Patient creates initial condition description"""
    if current_user.get("user_type") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access this")
    
    patient_id = current_user.get("user_id")
    
    # Check if progress already exists
    progress = db.query(models.PatientProgress).filter(
        models.PatientProgress.patient_id == patient_id
    ).first()
    
    if progress:
        # Update existing
        progress.initial_condition = data.initial_condition
    else:
        # Create new
        progress = models.PatientProgress(
            patient_id=patient_id,
            initial_condition=data.initial_condition,
            weekly_progress={},
            current_week=0
        )
        db.add(progress)
    
    db.commit()
    db.refresh(progress)
    return progress

@router.post("/weekly-progress", response_model=schemas.PatientProgressResponse)
def add_weekly_progress(
    data: schemas.WeeklyProgressCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Patient adds weekly progress"""
    if current_user.get("user_type") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access this")
    
    patient_id = current_user.get("user_id")
    
    # Get or create progress
    progress = db.query(models.PatientProgress).filter(
        models.PatientProgress.patient_id == patient_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Please add initial condition first")
    
    # Add weekly progress
    if progress.weekly_progress is None:
        progress.weekly_progress = {}
    
    week_key = f"week_{data.week_number}"
    progress.weekly_progress[week_key] = data.progress_text
    progress.current_week = data.week_number
    
    # Mark as modified for SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(progress, "weekly_progress")
    
    db.commit()
    db.refresh(progress)
    return progress

@router.put("/update-progress", response_model=schemas.PatientProgressResponse)
def update_progress(
    data: schemas.WeeklyProgressCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Patient updates existing weekly progress (for editing)"""
    if current_user.get("user_type") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access this")
    
    patient_id = current_user.get("user_id")
    
    # Get progress
    progress = db.query(models.PatientProgress).filter(
        models.PatientProgress.patient_id == patient_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")
    
    # Update weekly progress
    if progress.weekly_progress is None:
        progress.weekly_progress = {}
    
    week_key = f"week_{data.week_number}"
    progress.weekly_progress[week_key] = data.progress_text
    
    # Mark as modified for SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(progress, "weekly_progress")
    
    db.commit()
    db.refresh(progress)
    return progress

@router.get("/my-progress", response_model=schemas.PatientProgressResponse)
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Patient gets their own progress"""
    if current_user.get("user_type") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access this")
    
    patient_id = current_user.get("user_id")
    
    progress = db.query(models.PatientProgress).filter(
        models.PatientProgress.patient_id == patient_id
    ).first()
    
    if not progress:
        # Return empty progress
        return schemas.PatientProgressResponse(
            id=0,
            patient_id=patient_id,
            initial_condition=None,
            weekly_progress={},
            current_week=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    return progress

# Therapist endpoints
@router.get("/patients", response_model=List[schemas.PatientProgressHistory])
def get_all_patients_progress(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Therapist gets all their patients' progress"""
    if current_user.get("user_type") != "therapist":
        raise HTTPException(status_code=403, detail="Only therapists can access this")
    
    therapist_id = current_user.get("user_id")
    
    # Get all patients for this therapist
    patients = db.query(Patient).filter(Patient.therapist_id == therapist_id).all()
    
    result = []
    for patient in patients:
        # Get progress
        progress = db.query(models.PatientProgress).filter(
            models.PatientProgress.patient_id == patient.id
        ).first()
        
        # Get therapist note
        note = db.query(models.TherapistNote).filter(
            models.TherapistNote.patient_id == patient.id,
            models.TherapistNote.therapist_id == therapist_id
        ).first()
        
        result.append(schemas.PatientProgressHistory(
            patient_id=patient.id,
            patient_name=patient.name,
            patient_email=patient.email,
            conditions=patient.conditions,
            initial_condition=progress.initial_condition if progress else None,
            weekly_progress=progress.weekly_progress if progress else {},
            current_week=progress.current_week if progress else 0,
            therapist_note=note
        ))
    
    return result

@router.post("/therapist-note", response_model=schemas.TherapistNoteResponse)
def create_or_update_therapist_note(
    data: schemas.TherapistNoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Therapist creates or updates note for a specific week/initial of a patient"""
    if current_user.get("user_type") != "therapist":
        raise HTTPException(status_code=403, detail="Only therapists can access this")
    
    therapist_id = current_user.get("user_id")
    
    # Verify patient belongs to this therapist
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.therapist_id == therapist_id
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned to you")
    
    # Get or create note record
    note = db.query(models.TherapistNote).filter(
        models.TherapistNote.patient_id == data.patient_id,
        models.TherapistNote.therapist_id == therapist_id
    ).first()
    
    if note:
        # Update existing - add/update note for specific week
        if note.week_notes is None:
            note.week_notes = {}
        note.week_notes[data.week_key] = data.note_text
        # Mark as modified for SQLAlchemy to detect JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(note, "week_notes")
    else:
        # Create new
        note = models.TherapistNote(
            patient_id=data.patient_id,
            therapist_id=therapist_id,
            week_notes={data.week_key: data.note_text},
            ai_protocol_instruction=None
        )
        db.add(note)
    
    db.commit()
    db.refresh(note)
    return note

@router.post("/ai-protocol", response_model=schemas.TherapistNoteResponse)
def update_ai_protocol(
    data: schemas.AIProtocolUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Therapist updates AI protocol instruction for a patient"""
    if current_user.get("user_type") != "therapist":
        raise HTTPException(status_code=403, detail="Only therapists can access this")
    
    therapist_id = current_user.get("user_id")
    
    # Verify patient belongs to this therapist
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.therapist_id == therapist_id
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned to you")
    
    # Get or create note record
    note = db.query(models.TherapistNote).filter(
        models.TherapistNote.patient_id == data.patient_id,
        models.TherapistNote.therapist_id == therapist_id
    ).first()
    
    if note:
        note.ai_protocol_instruction = data.ai_protocol_instruction
    else:
        note = models.TherapistNote(
            patient_id=data.patient_id,
            therapist_id=therapist_id,
            week_notes={},
            ai_protocol_instruction=data.ai_protocol_instruction
        )
        db.add(note)
    
    db.commit()
    db.refresh(note)
    return note

@router.get("/patient/{patient_id}", response_model=schemas.PatientProgressHistory)
def get_patient_progress(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Therapist gets specific patient's progress"""
    if current_user.get("user_type") != "therapist":
        raise HTTPException(status_code=403, detail="Only therapists can access this")
    
    therapist_id = current_user.get("user_id")
    
    # Verify patient belongs to this therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == therapist_id
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned to you")
    
    # Get progress
    progress = db.query(models.PatientProgress).filter(
        models.PatientProgress.patient_id == patient_id
    ).first()
    
    # Get therapist note
    note = db.query(models.TherapistNote).filter(
        models.TherapistNote.patient_id == patient_id,
        models.TherapistNote.therapist_id == therapist_id
    ).first()
    
    return schemas.PatientProgressHistory(
        patient_id=patient.id,
        patient_name=patient.name,
        patient_email=patient.email,
        conditions=patient.conditions,
        initial_condition=progress.initial_condition if progress else None,
        weekly_progress=progress.weekly_progress if progress else {},
        current_week=progress.current_week if progress else 0,
        therapist_note=note
    )
