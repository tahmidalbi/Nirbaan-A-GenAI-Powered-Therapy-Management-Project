from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatGroupCreate(BaseModel):
    name: str


class ChatGroupMemberAdd(BaseModel):
    patient_id: int


class ChatMessageOut(BaseModel):
    id: int
    group_id: int
    sender_id: int
    sender_role: str
    sender_name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatGroupMemberOut(BaseModel):
    id: int
    patient_id: int
    joined_at: datetime

    class Config:
        from_attributes = True


class ChatGroupOut(BaseModel):
    id: int
    name: str
    therapist_id: int
    created_at: datetime
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True
