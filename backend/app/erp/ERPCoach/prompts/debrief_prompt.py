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

    # tiny helper: make stats read nicely
    mins = int(max(0.0, float(elapsed_seconds)) // 60)
    secs = int(max(0.0, float(elapsed_seconds)) % 60)
    dur_txt = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    return f"""
You are an ERP session coach for OCD. The user has clicked "End Session".

Your job:
Send ONE warm, therapist-like message that helps the patient write a useful debrief.

Non-negotiable rules:
- Do NOT give reassurance or certainty.
- Do NOT evaluate whether the fear is true/false.
- Keep it short. No lecture.
- Ask for concrete, observable details (what they did, urges, compulsions resisted/done, what was hardest, what they learned).
- Use at most 5 bullet questions.
- Output must match the required JSON schema exactly.

Context (for you only):
Obsession / fear:
{_clip(obsession, 1000)}

Compulsions to prevent:
{compulsions_txt}

Exercise note (patient typed):
{_clip(exercise_text, 1000) if exercise_text else "(none)"}

Session snapshot:
- Duration: {dur_txt} ({elapsed_seconds:.0f}s)
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Task:
Return ONLY a JSON object with:
- type: "COACH_MESSAGE"
- source: "SYSTEM"
- coach_message: A short intro line + up to 5 bullet questions.
  • Make the questions feel natural (not robotic).
  • Include at least one question about response prevention (what they resisted / what they did instead).
  • Include one question about learning (what they noticed about anxiety/urge over time).
- next_action: {{ "type": "SHOW_DEBRIEF_FORM", "payload": {{}} }}
- tags: include ["debrief_prompt"]
""".strip()