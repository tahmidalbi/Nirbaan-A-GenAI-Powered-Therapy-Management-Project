# ai_ladder_review_v2/ladder_review_agent/nodes/ladder_extractor.py
from __future__ import annotations

import os

from openai import OpenAI

from ..state import LadderReviewState
from ..schemas import LadderExtractionResponse
from ..prompts.ladder_extractor_prompt import build_ladder_extractor_prompt


def ladder_extractor_node(state: LadderReviewState) -> LadderReviewState:
    """
    LLM: normalize ladder raw text into structured obsession + compulsion list.
    """
    ladder_raw = (state.ladder_raw_text or "").strip()
    if not ladder_raw:
        state.ladder_items = []
        state.ladder_text = ""
        state.log_trace("ladder_extractor", {"ladder_items": 0})
        return state

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL", "gpt-5.3")

    prompt = build_ladder_extractor_prompt(ladder_raw)

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    out = resp.output_text  # type: ignore[attr-defined]
    parsed = LadderExtractionResponse.model_validate_json(out)

    state.ladder_items = [x.model_dump() for x in parsed.ladder_items]

    # compact summary for matching node
    compact = []
    for li in parsed.ladder_items:
        comp = "; ".join(li.compulsions) if li.compulsions else ""
        compact.append(f"- {li.obsession} || {comp}".strip())
    state.ladder_text = "\n".join(compact).strip()

    state.log_trace("ladder_extractor", {"ladder_items": len(state.ladder_items)})
    return state