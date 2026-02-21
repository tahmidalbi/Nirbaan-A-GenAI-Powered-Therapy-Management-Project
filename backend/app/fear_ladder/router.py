from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.deps import get_db
from app.fear_ladder.models import FearLadder, FearLadderItem, FearLadderStatus, AILadderReview, AILadderReviewStatus
from app.fear_ladder.schemas import (
    FearLadderCreate,
    FearLadderUpdate,
    FearLadderResponse,
    FearLadderWithPatientInfo,
    AILadderReviewResponse,
    AILadderReviewSummary
)
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.auth.utils import get_current_patient, get_current_therapist
from app.ai_ladder_review.tasks import detect_missing_ocd_structures_task

router = APIRouter(prefix="/fear-ladders", tags=["Fear Ladders"])


# Patient Endpoints
@router.post("/", response_model=FearLadderResponse, status_code=status.HTTP_201_CREATED)
async def create_fear_ladder(
    ladder_data: FearLadderCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Create a new fear ladder (patient only)
    """
    # Check if patient already has a pending or approved fear ladder
    existing_ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == current_patient.id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if existing_ladder and existing_ladder.status in [FearLadderStatus.pending, FearLadderStatus.approved]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have a {existing_ladder.status} fear ladder. Please update the existing one instead of creating a new one."
        )
    
    # Create fear ladder
    new_ladder = FearLadder(
        patient_id=current_patient.id,
        status=FearLadderStatus.pending
    )
    db.add(new_ladder)
    db.flush()
    
    # Sort items by SUDS and add them
    sorted_items = sorted(ladder_data.items, key=lambda x: x.suds)
    for idx, item_data in enumerate(sorted_items):
        ladder_item = FearLadderItem(
            fear_ladder_id=new_ladder.id,
            item=item_data.item,
            suds=item_data.suds,
            order_index=idx
        )
        db.add(ladder_item)
    
    db.commit()
    db.refresh(new_ladder)
    return new_ladder


@router.get("/my-ladder", response_model=FearLadderResponse)
async def get_my_fear_ladder(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get current patient's fear ladder
    """
    ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == current_patient.id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fear ladder found. Create one first."
        )
    
    return ladder


@router.put("/my-ladder", response_model=FearLadderResponse)
async def update_my_fear_ladder(
    ladder_data: FearLadderUpdate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Update current patient's fear ladder. If approved, creates a new pending ladder.
    """
    ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == current_patient.id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fear ladder found. Create one first."
        )
    
    # If current ladder is approved, create a new pending one instead of updating
    if ladder.status == FearLadderStatus.approved:
        # Create new ladder
        new_ladder = FearLadder(
            patient_id=current_patient.id,
            status=FearLadderStatus.pending
        )
        db.add(new_ladder)
        db.flush()
        
        # Add items to new ladder
        sorted_items = sorted(ladder_data.items, key=lambda x: x.suds)
        for idx, item_data in enumerate(sorted_items):
            ladder_item = FearLadderItem(
                fear_ladder_id=new_ladder.id,
                item=item_data.item,
                suds=item_data.suds,
                order_index=idx
            )
            db.add(ladder_item)
        
        db.commit()
        db.refresh(new_ladder)
        return new_ladder
    
    # If pending, update existing ladder
    # Delete existing items
    db.query(FearLadderItem).filter(
        FearLadderItem.fear_ladder_id == ladder.id
    ).delete()
    
    # Add new items
    sorted_items = sorted(ladder_data.items, key=lambda x: x.suds)
    for idx, item_data in enumerate(sorted_items):
        ladder_item = FearLadderItem(
            fear_ladder_id=ladder.id,
            item=item_data.item,
            suds=item_data.suds,
            order_index=idx
        )
        db.add(ladder_item)
    
    ladder.updated_at = datetime.utcnow()
    ladder.status = FearLadderStatus.pending
    
    db.commit()
    db.refresh(ladder)
    return ladder


# Therapist Endpoints
@router.get("/all", response_model=List[FearLadderWithPatientInfo])
async def get_all_fear_ladders(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get all fear ladders for therapist's patients
    """
    ladders = db.query(FearLadder).join(Patient).filter(
        Patient.therapist_id == current_therapist.id
    ).order_by(FearLadder.created_at.desc()).all()
    
    # Add patient info to each ladder
    result = []
    for ladder in ladders:
        ladder_dict = FearLadderResponse.model_validate(ladder).model_dump()
        ladder_dict['patient_name'] = ladder.patient.name
        ladder_dict['patient_email'] = ladder.patient.email
        result.append(ladder_dict)
    
    return result


@router.get("/patient/{patient_id}", response_model=FearLadderResponse)
async def get_patient_fear_ladder(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get a specific patient's fear ladder (therapist only)
    """
    # Verify patient belongs to therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you"
        )
    
    ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == patient_id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fear ladder found for this patient"
        )
    
    return ladder


@router.put("/patient/{patient_id}", response_model=FearLadderResponse)
async def update_patient_fear_ladder(
    patient_id: int,
    ladder_data: FearLadderUpdate,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Update a patient's fear ladder (therapist only)
    """
    # Verify patient belongs to therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you"
        )
    
    ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == patient_id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fear ladder found for this patient"
        )
    
    # Delete existing items
    db.query(FearLadderItem).filter(
        FearLadderItem.fear_ladder_id == ladder.id
    ).delete()
    
    # Add new items
    sorted_items = sorted(ladder_data.items, key=lambda x: x.suds)
    for idx, item_data in enumerate(sorted_items):
        ladder_item = FearLadderItem(
            fear_ladder_id=ladder.id,
            item=item_data.item,
            suds=item_data.suds,
            order_index=idx
        )
        db.add(ladder_item)
    
    ladder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ladder)
    return ladder


@router.post("/patient/{patient_id}/approve", response_model=FearLadderResponse)
async def approve_fear_ladder(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Approve a patient's fear ladder (therapist only)
    """
    # Verify patient belongs to therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you"
        )
    
    ladder = db.query(FearLadder).filter(
        FearLadder.patient_id == patient_id
    ).order_by(FearLadder.created_at.desc()).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fear ladder found for this patient"
        )
    
    if ladder.status == FearLadderStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fear ladder is already approved"
        )
    
    ladder.status = FearLadderStatus.approved
    ladder.approved_at = datetime.utcnow()
    ladder.approved_by = current_therapist.id
    ladder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ladder)
    return ladder


# AI Ladder Review Endpoints

@router.post("/{ladder_id}/submit-for-review", status_code=status.HTTP_202_ACCEPTED)
async def submit_ladder_for_ai_review(
    ladder_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Submit fear ladder for AI review (patient only).
    Creates a review task that analyzes intake + last 7 days logs.
    """
    # Verify ladder belongs to patient
    ladder = db.query(FearLadder).filter(
        FearLadder.id == ladder_id,
        FearLadder.patient_id == current_patient.id
    ).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fear ladder not found"
        )
    
    # Get patient's therapist
    patient = db.query(Patient).filter(Patient.id == current_patient.id).first()
    if not patient or not patient.therapist_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No therapist assigned to your account"
        )
    
    # Check if there's already a recent review
    existing_review = db.query(AILadderReview).filter(
        AILadderReview.ladder_id == ladder_id,
        AILadderReview.status.in_([AILadderReviewStatus.queued, AILadderReviewStatus.running])
    ).first()
    
    if existing_review:
        return {
            "message": "AI review already in progress",
            "review_id": existing_review.id,
            "status": existing_review.status.value
        }
    
    # Create new review record
    review = AILadderReview(
        ladder_id=ladder_id,
        patient_id=current_patient.id,
        therapist_id=patient.therapist_id,
        status=AILadderReviewStatus.queued,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Enqueue Celery task
    detect_missing_ocd_structures_task.delay(review.id)
    
    return {
        "message": "AI review queued successfully",
        "review_id": review.id,
        "status": review.status.value
    }


@router.get("/{ladder_id}/ai-review", response_model=AILadderReviewSummary)
async def get_ladder_ai_review(
    ladder_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get AI review results for a ladder (therapist only).
    Returns suggestions for missing obsession-compulsion pairs.
    """
    # Verify ladder belongs to therapist's patient
    ladder = db.query(FearLadder).join(Patient).filter(
        FearLadder.id == ladder_id,
        Patient.therapist_id == current_therapist.id
    ).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fear ladder not found or not assigned to you"
        )
    
    # Get most recent review for this ladder
    review = db.query(AILadderReview).filter(
        AILadderReview.ladder_id == ladder_id
    ).order_by(AILadderReview.created_at.desc()).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI review found for this ladder. Patient needs to submit it for review first."
        )
    
    # Return summary format
    return AILadderReviewSummary(
        status=review.status.value,
        suggestions=[s for s in review.suggestions] if review.status == AILadderReviewStatus.completed else [],
        error_message=review.error_message
    )


@router.get("/{ladder_id}/ai-review/full", response_model=AILadderReviewResponse)
async def get_full_ladder_ai_review(
    ladder_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get full AI review details including all metadata (therapist only).
    """
    # Verify ladder belongs to therapist's patient
    ladder = db.query(FearLadder).join(Patient).filter(
        FearLadder.id == ladder_id,
        Patient.therapist_id == current_therapist.id
    ).first()
    
    if not ladder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fear ladder not found or not assigned to you"
        )
    
    # Get most recent review for this ladder
    review = db.query(AILadderReview).filter(
        AILadderReview.ladder_id == ladder_id
    ).order_by(AILadderReview.created_at.desc()).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI review found for this ladder"
        )
    
    return review
