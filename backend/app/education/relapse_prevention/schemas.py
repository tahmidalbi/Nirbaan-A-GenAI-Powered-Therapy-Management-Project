# app/education/relapse_prevention/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Source(BaseModel):
    type: Literal["kb", "web"]
    title: str
    resource_id: Optional[int] = None
    url: Optional[str] = None


class Section(BaseModel):
    id: str
    title: str
    content_markdown: str
    key_points: List[str] = Field(default_factory=list, max_length=10)


class RelapsePreventionEducation(BaseModel):
    module: Literal["relapse_prevention_education"] = "relapse_prevention_education"
    topic: str
    reading_level: Literal["simple", "standard"] = "simple"
    sections: List[Section]
    sources: List[Source]
    disclaimer: str


class KBJudge(BaseModel):
    kb_sufficient: bool
    reason: str = Field(default="")
