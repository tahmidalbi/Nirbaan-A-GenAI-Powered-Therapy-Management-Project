# ai_ladder_review_v2/ladder_review_agent/schemas.py
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


# -----------------------------
# Ladder extractor schema
# -----------------------------

class LadderItem(BaseModel):
    id: str = Field(..., description='Stable id like "L1"')
    obsession: str
    compulsions: List[str]


class LadderExtractionResponse(BaseModel):
    ladder_items: List[LadderItem] = Field(default_factory=list)


# -----------------------------
# Symptom finder schema
# -----------------------------

SourceType = Literal["intake", "daily_log"]


class EvidenceItem(BaseModel):
    source_type: SourceType
    source_id: str
    source_date: str  # "YYYY-MM-DD"
    field_name: str
    quote_text: str


class CandidatePattern(BaseModel):
    id: str = Field(..., description='Stable id like "C1"')
    label: str
    obsession: str
    compulsions: List[str] = Field(default_factory=list)
    potential_pattern: bool = False
    evidence: List[EvidenceItem] = Field(default_factory=list)


class SymptomFinderResponse(BaseModel):
    candidates: List[CandidatePattern] = Field(default_factory=list)


# -----------------------------
# Checker schema
# -----------------------------

class CheckerResponse(BaseModel):
    recheck: bool
    reason: str
    recheck_query: str = ""


# -----------------------------
# Hidden matcher schema
# -----------------------------

class HiddenMatcherResponse(BaseModel):
    missing_ids: List[str] = Field(default_factory=list)