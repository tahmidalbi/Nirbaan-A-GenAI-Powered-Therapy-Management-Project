# ai_ladder_review_v2/ladder_review_agent/prompts/hidden_matcher_prompt.py
from __future__ import annotations


def build_hidden_matcher_prompt(
    ladder_items_json: str,
    candidates_all_json: str,
) -> str:
    """
    Compares extracted candidates vs ladder items and returns missing candidate IDs only.
    Output must be strict JSON (no markdown).
    """
    return f"""
You are matching extracted OCD patterns against a patient's fear ladder to find what is missing.

INPUT A: LADDER ITEMS (normalized JSON)
{ladder_items_json}

INPUT B: EXTRACTED CANDIDATES (normalized JSON)
{candidates_all_json}

TASK:
Return the IDs of candidates that are NOT represented in the ladder.

Representation / matching rules:
- Consider a candidate "represented" if the ladder includes a similar obsession theme AND a similar compulsion type.
- Be tolerant of wording differences (synonyms).
- If a candidate is only a "potential_pattern" with unclear compulsion, treat it as represented ONLY if the ladder clearly contains that same trigger/theme; otherwise mark missing for therapist follow-up.
- Do not invent new candidates. Only choose from the provided candidate IDs.
- Do not rewrite the candidate text. Output IDs only.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "missing_ids": ["C1", "C7"]
}}

RULES:
- Output ONLY valid JSON.
- No markdown, no commentary.
""".strip()