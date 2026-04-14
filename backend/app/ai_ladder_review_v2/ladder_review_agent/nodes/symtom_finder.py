# ai_ladder_review_v2/ladder_review_agent/nodes/symptom_finder.py
from __future__ import annotations

import os
import re
from typing import Dict

from openai import OpenAI

from ..state import LadderReviewState
from ..schemas import SymptomFinderResponse
from ..prompts.symtom_finder_prompt import build_symptom_finder_prompt


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _candidate_key(c: Dict) -> str:
    """
    Simple dedupe key:
      obsession + first compulsion (if any)
    """
    obs = _norm(c.get("obsession", ""))
    comps = c.get("compulsions") or []
    first = _norm(comps[0]) if comps else ""
    return f"{obs}||{first}"


def symptom_finder_node(state: LadderReviewState) -> LadderReviewState:
    """
    LLM: extract obsession+compulsion candidates from:
      - taxonomy_context_text (retrieved)
      - intake_text
      - current batch text
    """
    batch = state.current_batch()
    if not batch:
        return state

    taxonomy_ctx = (state.taxonomy_context_text or "").strip()
    intake_text = (state.intake_text or "").strip() if state.batch_index == 0 else ""
    batch_text = (batch.get("text") or "").strip()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL", "gpt-5.3")

    prompt = build_symptom_finder_prompt(
        taxonomy_context_text=taxonomy_ctx,
        intake_text=intake_text,
        batch_text=batch_text,
        recheck_mode=(state.batch_retry_count > 0),
    )

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    out = resp.output_text  # type: ignore[attr-defined]
    parsed = SymptomFinderResponse.model_validate_json(out)

    batch_candidates = [c.model_dump() for c in parsed.candidates]

    # merge into candidates_all (dedupe)
    existing = {_candidate_key(c): c for c in (state.candidates_all or [])}
    for c in batch_candidates:
        k = _candidate_key(c)
        if k not in existing:
            existing[k] = c

    state.batch_candidates = batch_candidates
    state.candidates_all = list(existing.values())

    state.log_trace(
        "symptom_finder",
        {
            "batch_id": batch.get("batch_id"),
            "retry": state.batch_retry_count,
            "batch_candidates": len(batch_candidates),
            "candidates_all": len(state.candidates_all),
        },
    )
    return state