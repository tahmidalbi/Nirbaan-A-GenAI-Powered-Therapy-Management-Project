# ai_ladder_review_v2/ladder_review_agent/prompts/checker_prompt.py
from __future__ import annotations


def build_checker_prompt(
    batch_text: str,
    extracted_candidates_json: str,
) -> str:
    """
    LLM decides whether to recheck the SAME batch.
    MUST output:
      - recheck (bool)
      - reason (string)
      - recheck_query (string)  [keywords to bias retrieval next time]
    """
    return f"""
You are a quality-checker for an OCD symptom extraction system.

You will decide whether the SAME batch should be rechecked (run extraction again).
Recheck should be TRUE only if it is likely that important OCD-structured patterns were missed.

You must be conservative: do NOT request recheck unless there is strong evidence of missing patterns.

BATCH TEXT:
{batch_text}

EXTRACTED CANDIDATES (JSON):
{extracted_candidates_json}

DECIDE:
Return recheck=true only if at least one of these is true:
1) The batch clearly contains repeated cognitive signals (e.g., replaying/analyzing/mentally checking) but the extracted candidates list has no mental-compulsion-like item.
2) The batch mentions attention stuck on sensations/awareness (e.g., noticing eye/blink/breath) but no somatic/sensorimotor-like item was extracted.
3) The batch contains reassurance signals (e.g., google/search/ask/confirm) but no reassurance-like item was extracted.
4) The batch contains avoidance signals (avoid/escape/didn't go) but no avoidance-like item was extracted.
5) The extraction output is extremely small compared to batch content (e.g., many log entries but only 0–1 candidates), AND the batch has anxiety/uncertainty language.

If recheck=true, you MUST provide:
- a short reason
- a recheck_query: a short space-separated keyword string to bias taxonomy retrieval next time.
  This query must be derived ONLY from batch signals (not hardcoded). Example:
  "rumination mental checking replaying analysis reassurance google confirm"
If recheck=false, still output a short reason and an empty recheck_query.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "recheck": true,
  "reason": "string",
  "recheck_query": "string"
}}

RULES:
- Output ONLY valid JSON.
- No markdown, no commentary.
""".strip()