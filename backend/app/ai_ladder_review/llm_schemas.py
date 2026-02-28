# app/ai_ladder_review/llm_schemas.py
from __future__ import annotations

from typing import List, Literal, Optional, Set

from pydantic import BaseModel, Field, ConfigDict, model_validator


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Literal["intake", "daily_log"]
    source_id: str
    date: Optional[str] = None  # "YYYY-MM-DD" or null
    field_name: str
    quote_text: str = Field(min_length=1, max_length=280)


class StructureItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    obsession: str = Field(min_length=3)
    compulsions: List[str] = Field(min_length=1)
    rationale: str = Field(min_length=5)
    evidence: List[EvidenceItem] = Field(min_length=2)

    @model_validator(mode="after")
    def _ensure_evidence_has_intake_or_log(self) -> "StructureItem":
        # Require >=2 evidence overall (already enforced) and ensure at least one source_id exists.
        # (Extra safety: If evidence list is present, ensure quote_text non-empty handled by EvidenceItem.)
        return self


class ExtractStructuresResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structures: List[StructureItem]


class CompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_ids: List[str] = Field(default_factory=list)


def validate_missing_ids(missing_ids: List[str], allowed_ids: Set[str]) -> None:
    bad = [x for x in missing_ids if x not in allowed_ids]
    if bad:
        raise ValueError(f"Call2 returned invalid ids (not in allowed set): {bad}")