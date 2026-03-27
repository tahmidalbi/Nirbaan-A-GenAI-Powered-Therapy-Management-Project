from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import get_current_therapist
from app.therapists.models import Therapist

from app.NirbaanAITherapist.chat_service import TherapistAIChatService
from app.NirbaanAITherapist.schemas import (
    ResumePatientAnalysisResponse,
    SubmitClarificationAnswerRequest,
    TherapistAIChatHistoryResponse,
    TherapistAIChatMessageOut,
    TherapistAIChatThreadOut,
    TherapistChatSendRequest,
    TherapistChatSendResponse,
)


router = APIRouter(
    prefix="/therapist/ai-chat",
    tags=["Therapist AI Chat"],
)


@router.post(
    "/send",
    response_model=TherapistChatSendResponse,
    status_code=status.HTTP_200_OK,
)
def send_therapist_ai_message(
    payload: TherapistChatSendRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Send a therapist message to the AI.
    May return:
    - direct assistant reply
    - or a clarification request
    """
    service = TherapistAIChatService(db)

    try:
        return service.send_message(
            therapist_id=current_therapist.id,
            patient_id=payload.patient_id,
            message=payload.message,
            thread_id=payload.thread_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/analysis-runs/{analysis_run_id}/clarification",
    response_model=ResumePatientAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def submit_analysis_clarification_answer(
    analysis_run_id: int,
    payload: SubmitClarificationAnswerRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Submit therapist answer to the AI clarification question and resume analysis.
    """
    service = TherapistAIChatService(db)

    try:
        return service.submit_clarification_answer(
            therapist_id=current_therapist.id,
            analysis_run_id=analysis_run_id,
            answer=payload.answer,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/threads/{thread_id}",
    response_model=TherapistAIChatHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_therapist_ai_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Get one therapist AI chat thread with all messages.
    """
    service = TherapistAIChatService(db)

    try:
        thread = service.get_thread(
            therapist_id=current_therapist.id,
            thread_id=thread_id,
        )
        messages = service.get_thread_messages(
            therapist_id=current_therapist.id,
            thread_id=thread_id,
        )

        return TherapistAIChatHistoryResponse(
            thread=TherapistAIChatThreadOut.model_validate(thread),
            messages=[
                TherapistAIChatMessageOut.model_validate(message)
                for message in messages
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/threads",
    response_model=List[TherapistAIChatThreadOut],
    status_code=status.HTTP_200_OK,
)
def list_therapist_ai_threads(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    List all therapist AI chat threads for the current therapist.
    """
    service = TherapistAIChatService(db)

    threads = service.list_threads(therapist_id=current_therapist.id)

    return [
        TherapistAIChatThreadOut.model_validate(thread)
        for thread in threads
    ]