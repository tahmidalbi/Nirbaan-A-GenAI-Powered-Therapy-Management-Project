from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ChatRole


class PsychoeducationChatSendRequest(BaseModel):
    thread_id: Optional[int] = Field(
        default=None,
        description="Existing thread ID. If null, backend may create a new thread.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Patient message sent to the psychoeducation chatbot.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value


class PsychoeducationChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    role: ChatRole
    content: str
    created_at: datetime


class PsychoeducationChatThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PsychoeducationChatThreadDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[PsychoeducationChatMessageOut] = []


class PsychoeducationChatSendResponse(BaseModel):
    thread_id: int
    user_message: PsychoeducationChatMessageOut
    assistant_message: PsychoeducationChatMessageOut
    used_web_fallback: bool = False


class PsychoeducationChatHistoryResponse(BaseModel):
    thread: PsychoeducationChatThreadOut
    messages: List[PsychoeducationChatMessageOut]