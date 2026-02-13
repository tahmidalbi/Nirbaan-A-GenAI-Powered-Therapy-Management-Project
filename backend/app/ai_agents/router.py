"""
Nirbaan AI Router - REST API for Protocol Generation Pipeline

This module provides FastAPI endpoints for the multi-agent therapy protocol
generation system using LangGraph workflow.

Endpoints:
- POST /nirbaan-ai/generate-protocol - Start protocol generation for a patient
- POST /nirbaan-ai/resume-clarification - Resume after therapist answers clarification
- GET /nirbaan-ai/protocols/{patient_id} - Get all protocols for a patient
- GET /nirbaan-ai/protocol/{protocol_id} - Get specific protocol details

Author: Nirbaan AI Research Team
Date: February 11, 2026
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid

from app.database.deps import get_db
from app.auth.utils import get_current_user
from app.patients.models import Patient

# Import LangGraph workflow (with error handling for imports)
try:
    from .langgraph_workflow import run_protocol_generation, resume_after_clarification
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LangGraph workflow not available: {e}")
    LANGGRAPH_AVAILABLE = False
    MemorySaver = None  # Placeholder for type checking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nirbaan-ai", tags=["nirbaan-ai"])

# Store checkpointers by thread_id (for clarification resume functionality)
_checkpointers: Dict[str, Any] = {}

# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class GenerateProtocolRequest(BaseModel):
    """Request schema for generating a therapy protocol"""
    patient_id: int = Field(..., description="ID of the patient")
    session_focus: Optional[str] = Field(
        None,
        description="Optional specific focus for the session (e.g., 'harm OCD exposure')"
    )


class ClarificationAnswersRequest(BaseModel):
    """Request schema for submitting clarification answers"""
    thread_id: str = Field(..., description="Thread ID from initial generation")
    answers: Dict[str, Any] = Field(..., description="Answers to clarification questions")


class GenerateProtocolResponse(BaseModel):
    """Response schema for protocol generation"""
    status: str = Field(..., description="Status: 'success', 'needs_clarification', 'halted', 'error'")
    protocol: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    confidence_tier: Optional[str] = None
    clarification_questions: Optional[List[Dict[str, Any]]] = None
    thread_id: Optional[str] = None
    halt_reason: Optional[str] = None
    audit_trail: Optional[List[Dict[str, Any]]] = None
    processing_time_seconds: Optional[float] = None
    patient_info: Optional[Dict[str, Any]] = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_confidence_tier(score: float) -> str:
    """Get confidence tier label from score."""
    if score >= 0.9:
        return "very_high"
    elif score >= 0.7:
        return "high"
    elif score >= 0.5:
        return "moderate"
    elif score >= 0.3:
        return "low"
    else:
        return "very_low"


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.post("/generate-protocol", response_model=GenerateProtocolResponse)
async def generate_protocol(
    request: GenerateProtocolRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a 60-minute therapy protocol for a patient using LangGraph pipeline.
    """
    logger.info("=" * 80)
    logger.info("🚀 REAL LANGGRAPH ENDPOINT HIT - /generate-protocol")
    logger.info(f"   ⚠️⚠️⚠️ PATIENT ID: {request.patient_id} ⚠️⚠️⚠️")
    logger.info(f"   Session Focus: {request.session_focus or 'None'}")
    logger.info("=" * 80)

    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can generate protocols"
        )

    if not LANGGRAPH_AVAILABLE:
        logger.error("❌ LangGraph not available - import failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI protocol generation service is not available"
        )

    therapist_id = current_user["user_id"]

    # Verify patient belongs to this therapist
    patient = db.execute(
        select(Patient).where(
            Patient.id == request.patient_id,
            Patient.therapist_id == therapist_id
        )
    ).scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you"
        )

    start_time = datetime.now()

    try:
        # ✅ fresh checkpointer per run
        checkpointer = MemorySaver()
        logger.info(f"Created fresh MemorySaver checkpointer id={id(checkpointer)}")

        # Run pipeline
        result = await run_protocol_generation(
            patient_id=request.patient_id,
            therapist_id=therapist_id,
            db_session=db,
            session_focus=request.session_focus,
            checkpointer=checkpointer
        )

        thread_id = result.get("thread_id")
        if thread_id:
            _checkpointers[thread_id] = checkpointer
            logger.info(f"Stored checkpointer for thread {thread_id}")

        processing_time = (datetime.now() - start_time).total_seconds()

        confidence_score = result.get("confidence_score")
        confidence_tier = get_confidence_tier(confidence_score) if isinstance(confidence_score, (int, float)) else None

        return GenerateProtocolResponse(
            status=result.get("status", "error"),
            protocol=result.get("final_protocol"),
            confidence_score=confidence_score,
            confidence_tier=confidence_tier,
            clarification_questions=result.get("clarification_questions"),
            thread_id=thread_id,
            halt_reason=result.get("halt_reason"),
            audit_trail=result.get("audit_trail"),
            processing_time_seconds=round(processing_time, 2),
            patient_info={
                "id": patient.id,
                "name": patient.name,
                "conditions": patient.conditions,
                "conditions_description": patient.conditions_description
            }
        )

    except Exception as e:
        logger.error(f"Protocol generation failed: {e}", exc_info=True)
        processing_time = (datetime.now() - start_time).total_seconds()
        return GenerateProtocolResponse(
            status="error",
            halt_reason=str(e),
            processing_time_seconds=round(processing_time, 2),
            patient_info={
                "id": patient.id,
                "name": patient.name,
                "conditions": patient.conditions
            }
        )


@router.post("/resume-clarification", response_model=GenerateProtocolResponse)
async def resume_after_clarification_endpoint(
    request: ClarificationAnswersRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resume protocol generation after therapist provides clarification answers.
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can generate protocols"
        )

    if not LANGGRAPH_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI protocol generation service is not available"
        )

    start_time = datetime.now()

    try:
        checkpointer = _checkpointers.get(request.thread_id)
        if not checkpointer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active session found for thread {request.thread_id}"
            )

        # ✅ IMPORTANT: pass db_session to resume
        result = await resume_after_clarification(
            thread_id=request.thread_id,
            clarification_answers=request.answers,
            checkpointer=checkpointer,
            db_session=db
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        confidence_score = result.get("confidence_score")
        confidence_tier = get_confidence_tier(confidence_score) if isinstance(confidence_score, (int, float)) else None

        return GenerateProtocolResponse(
            status=result.get("status", "error"),
            protocol=result.get("final_protocol"),
            confidence_score=confidence_score,
            confidence_tier=confidence_tier,
            clarification_questions=None,
            thread_id=request.thread_id,
            halt_reason=result.get("halt_reason"),
            audit_trail=result.get("audit_trail"),
            processing_time_seconds=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        processing_time = (datetime.now() - start_time).total_seconds()
        return GenerateProtocolResponse(
            status="error",
            halt_reason=str(e),
            processing_time_seconds=round(processing_time, 2)
        )


@router.get("/patients-for-protocol")
async def get_patients_for_protocol(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of patients available for protocol generation.
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access this endpoint"
        )

    therapist_id = current_user["user_id"]

    patients = db.execute(
        select(Patient).where(Patient.therapist_id == therapist_id)
    ).scalars().all()

    patient_list = []
    from app.sessions.models import TherapySession

    for patient in patients:
        session_count = db.execute(
            select(TherapySession).where(TherapySession.patient_id == patient.id)
        ).scalars().all()

        patient_list.append({
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "conditions": patient.conditions,
            "conditions_description": patient.conditions_description,
            "session_count": len(session_count),
            "created_at": patient.created_at.isoformat() if patient.created_at else None
        })

    return {"patients": patient_list}
