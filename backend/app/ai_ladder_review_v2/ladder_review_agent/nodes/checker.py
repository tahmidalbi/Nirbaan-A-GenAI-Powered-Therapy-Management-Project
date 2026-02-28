# ai_ladder_review_v2/ladder_review_agent/nodes/checker.py
from __future__ import annotations

import json
import os

from openai import OpenAI

from ..state import LadderReviewState
from ..schemas import CheckerResponse
from ..prompts.checker_prompt import build_checker_prompt


def checker_node(state: LadderReviewState) -> LadderReviewState:
    """
    LLM: decide whether to recheck same batch.
    Must output recheck_query to bias retrieval if recheck=true.
    """
    batch = state.current_batch()
    if not batch:
        return state

    batch_text = (batch.get("text") or "").strip()
    extracted_json = json.dumps({"candidates": state.batch_candidates or []}, ensure_ascii=False)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL", "gpt-5.2")

    prompt = build_checker_prompt(
        batch_text=batch_text,
        extracted_candidates_json=extracted_json,
    )

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    out = resp.output_text  # type: ignore[attr-defined]
    parsed = CheckerResponse.model_validate_json(out)

    state.recheck = bool(parsed.recheck)
    state.recheck_reason = parsed.reason
    state.recheck_query = (parsed.recheck_query or "").strip()

    state.log_trace(
        "checker",
        {
            "batch_id": batch.get("batch_id"),
            "retry": state.batch_retry_count,
            "recheck": state.recheck,
            "reason": state.recheck_reason,
            "recheck_query": state.recheck_query,
        },
    )
    return state