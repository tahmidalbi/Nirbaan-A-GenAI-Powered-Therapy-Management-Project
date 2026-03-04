# app/erp/ERPCoach/prompts/debrief_prompt.py
from __future__ import annotations

from typing import List, Optional


def _clip(text: Optional[str], max_chars: int = 1200) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[:max_chars].rstrip() + "…"


def build_debrief_prompt(
    *,
    obsession: str,
    compulsions: List[str],
    exercise_text: Optional[str],
    elapsed_seconds: float,
    suds_peak: Optional[int],
    suds_latest: Optional[int],
) -> str:
    compulsions_txt = "\n".join([f"- {c}" for c in (compulsions or [])]) or "- (none)"
    return f"""
You are an ERP session coach. The user has clicked "End Session".
Your job: send ONE short message that prompts the patient to write a session debrief.

Rules:
- Keep it short and structured.
- Do NOT give reassurance.
- Ask for concrete details (what they did, what urges, what they resisted, what was hardest, what they learned).
- Output must match the required JSON schema.

Context:
Obsessive fear / obsession:
{_clip(obsession, 1000)}

Compulsions to prevent:
{compulsions_txt}

Exercise note:
{_clip(exercise_text, 1000) if exercise_text else "(none)"}

Session stats:
- Duration seconds: {elapsed_seconds:.0f}
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Task:
Return JSON:
- type: COACH_MESSAGE
- source: SYSTEM
- coach_message: Ask them to write the debrief (5 bullet questions max)
- next_action.type must be SHOW_DEBRIEF_FORM
- tags include ["debrief_prompt"]
""".strip()