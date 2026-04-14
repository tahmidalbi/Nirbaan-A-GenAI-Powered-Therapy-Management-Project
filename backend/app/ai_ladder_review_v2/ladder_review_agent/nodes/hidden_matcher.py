# ai_ladder_review_v2/ladder_review_agent/nodes/hidden_matcher.py
from __future__ import annotations

import json
import os

from openai import OpenAI

from ..state import LadderReviewState
from ..schemas import HiddenMatcherResponse
from ..prompts.hidden_matcher_prompt import build_hidden_matcher_prompt


def hidden_matcher_node(state: LadderReviewState) -> LadderReviewState:
    """
    LLM: compare normalized ladder items vs extracted candidates_all.
    Output missing_ids only.
    """
    ladder_items_json = json.dumps({"ladder_items": state.ladder_items or []}, ensure_ascii=False)
    candidates_all_json = json.dumps({"candidates": state.candidates_all or []}, ensure_ascii=False)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL", "gpt-5.3")

    prompt = build_hidden_matcher_prompt(
        ladder_items_json=ladder_items_json,
        candidates_all_json=candidates_all_json,
    )

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    out = resp.output_text  # type: ignore[attr-defined]
    parsed = HiddenMatcherResponse.model_validate_json(out)

    state.missing_ids = parsed.missing_ids

    state.log_trace("hidden_matcher", {"missing_ids_count": len(state.missing_ids)})
    return state