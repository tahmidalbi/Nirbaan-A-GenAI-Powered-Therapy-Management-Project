from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.NirbaanAIPatient.chat_service import PsychoeducationChatService
from app.NirbaanAIPatient.models import PsychoeducationChatThread
from app.NirbaanAIPatient.schemas import (
    PsychoeducationChatHistoryResponse,
    PsychoeducationChatMessageOut,
    PsychoeducationChatSendRequest,
    PsychoeducationChatSendResponse,
    PsychoeducationChatThreadOut,
)
from app.patients.models import Patient
from app.auth.utils import get_current_patient


router = APIRouter(
    prefix="/patient/psychoeducation-chat",
    tags=["Patient Psychoeducation Chat"],
)


@router.post(
    "/send",
    response_model=PsychoeducationChatSendResponse,
    status_code=status.HTTP_200_OK,
)
def send_psychoeducation_message(
    payload: PsychoeducationChatSendRequest,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Send a message to the psychoeducation chatbot.
    Creates a new thread if thread_id is not provided.
    """
    service = PsychoeducationChatService(db)

    try:
        return service.send_message(
            patient_id=current_patient.id,
            message=payload.message,
            thread_id=payload.thread_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/threads/{thread_id}",
    response_model=PsychoeducationChatHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_psychoeducation_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Get one psychoeducation chat thread with all its messages.
    """
    service = PsychoeducationChatService(db)

    try:
        thread = service.get_thread(
            patient_id=current_patient.id,
            thread_id=thread_id,
        )
        messages = service.get_thread_messages(
            patient_id=current_patient.id,
            thread_id=thread_id,
        )

        return PsychoeducationChatHistoryResponse(
            thread=PsychoeducationChatThreadOut.model_validate(thread),
            messages=[
                PsychoeducationChatMessageOut.model_validate(message)
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
    response_model=List[PsychoeducationChatThreadOut],
    status_code=status.HTTP_200_OK,
)
def list_psychoeducation_threads(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    List all psychoeducation chat threads for the current patient.
    Most recent first.
    """
    threads = (
        db.query(PsychoeducationChatThread)
        .filter(PsychoeducationChatThread.patient_id == current_patient.id)
        .order_by(
            PsychoeducationChatThread.updated_at.desc(),
            PsychoeducationChatThread.id.desc(),
        )
        .all()
    )

    return [
        PsychoeducationChatThreadOut.model_validate(thread)
        for thread in threads
    ]