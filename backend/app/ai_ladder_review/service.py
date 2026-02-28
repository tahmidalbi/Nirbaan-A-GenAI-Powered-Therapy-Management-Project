# app/ai_ladder_review/service.py
from __future__ import annotations

from typing import Any, Dict, List

from app.ai_ladder_review.llm_client import LLMClient
from app.ai_ladder_review.llm_schemas import (
    CompareResponse,
    ExtractStructuresResponse,
    StructureItem,
    validate_missing_ids,
)
from app.ai_ladder_review.prompts import build_call1_messages, build_call2_messages


class AILadderReviewService:
    """
    Orchestrates:
      Call 1 (extract structures) -> validate
      Call 2 (compare vs ladder)  -> validate subset
    Returns only missing StructureItem objects (with evidence).
    """

    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    def extract_structures(self, payload: Dict[str, Any]) -> ExtractStructuresResponse:
        messages = build_call1_messages(payload)
        raw = self.client.call_json(messages=messages, temperature=0.0, max_retries=1)
        parsed = ExtractStructuresResponse.model_validate(raw)

        # Extra safety: ensure evidence >=2 (already enforced by Field(min_length=2))
        return parsed

    def compare_against_ladder(
        self,
        *,
        structures_response: ExtractStructuresResponse,
        ladder_text: str,
    ) -> CompareResponse:
        structures_json: Dict[str, Any] = structures_response.model_dump()
        messages = build_call2_messages(structures_json=structures_json, ladder_text=ladder_text)
        raw = self.client.call_json(messages=messages, temperature=0.0, max_retries=1)
        parsed = CompareResponse.model_validate(raw)

        allowed_ids = {s.id for s in structures_response.structures}
        validate_missing_ids(parsed.missing_ids, allowed_ids)

        return parsed

    def run_review(self, payload: Dict[str, Any], ladder_text: str) -> List[StructureItem]:
        extracted = self.extract_structures(payload)
        compared = self.compare_against_ladder(structures_response=extracted, ladder_text=ladder_text)

        missing_set = set(compared.missing_ids)
        missing_structures = [s for s in extracted.structures if s.id in missing_set]

        return missing_structures