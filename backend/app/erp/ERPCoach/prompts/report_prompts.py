# app/erp/ERPCoach/prompts/report_prompts.py
from __future__ import annotations

from typing import List, Optional


def _clip(text: Optional[str], max_chars: int = 1800) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[:max_chars].rstrip() + "…"


def _bullet(items: List[str], max_items: int = 6) -> str:
    items = [x.strip() for x in (items or []) if x and x.strip()]
    items = items[:max_items]
    if not items:
        return "- (none)"
    return "\n".join([f"- {x}" for x in items])


def build_session_facts_prompt(
    *,
    obsession: str,
    compulsions: List[str],
    exercise_text: Optional[str],
    transcript_block: str,
    suds_points_block: str,
    patient_debrief_text: str,
    prior_summaries: List[str],
) -> str:
    """
    Step 1 in report pipeline:
    Convert raw transcript + debrief + SUDS points into compact factual bullets.
    """
    return f"""
You are helping summarize an ERP exposure session. Produce compact factual bullets (no reassurance).

Rules:
- Be factual and specific.
- Do not psychoanalyze. Do not reassure.
- Focus on ERP-relevant facts: exposure actions, urges, compulsions resisted/done, avoidance, safety behaviors, learning.

Context:
Obsession:
{_clip(obsession, 1200)}

Compulsions to prevent:
{_bullet(compulsions, 12)}

Exercise note:
{_clip(exercise_text, 1200) if exercise_text else "(none)"}

Prior sessions (continuity):
{_bullet(prior_summaries, 3)}

SUDS series (elapsed_seconds -> value):
{suds_points_block or "(no SUDS readings)"}

Transcript (recent):
{transcript_block or "(no transcript)"}

Patient debrief (what they said after ending):
{_clip(patient_debrief_text, 2000)}

Task:
Return a concise bullet list with sections:
- What exposure they did (1–4 bullets)
- Urges/compulsions (resisted vs performed) (1–6 bullets)
- Avoidance/safety behaviors noticed (0–4 bullets)
- Key learning / what helped (0–4 bullets)

Keep total under ~25 bullets.
""".strip()


def build_therapist_report_prompt(
    *,
    session_facts: str,
    elapsed_seconds: float,
    suds_peak: Optional[int],
    suds_latest: Optional[int],
) -> str:
    """
    Step 2: Generate strict JSON for therapist report schema.
    """
    return f"""
You are generating a therapist-facing ERP session report as STRICT JSON.

Rules:
- Use the provided facts. Do not invent details.
- Do not provide reassurance.
- Keep lists short and clinically useful.

Session stats:
- Duration seconds: {elapsed_seconds:.0f}
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- End/Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Extracted session facts:
{session_facts}

Task:
Return ONLY a JSON object matching TherapistReportJSON schema with:
- session_overview (include duration, peak/end suds)
- suds_curve_summary (1 short sentence)
- what_happened (bullets)
- compulsions_urges
- response_prevention_successes
- avoidance_or_safety_behaviors
- key_learning
- recommend_next_step (one concrete suggestion)
- risk_flags (usually empty; only if truly indicated by facts)
""".strip()


def build_patient_feedback_prompt(
    *,
    session_facts: str,
    elapsed_seconds: float,
    suds_peak: Optional[int],
    suds_latest: Optional[int],
) -> str:
    """
    Step 3: Generate strict JSON for patient feedback schema.

    IMPORTANT:
    - Do NOT invent wins.
    - If there were no clear wins in the session facts, return an empty list for `wins`.
    """

    return f"""
You are generating patient-facing ERP feedback as STRICT JSON.

Core Rules:
- Be supportive but NOT reassuring (do NOT say things like "you are definitely safe").
- Do NOT invent wins or progress.
- If there were no clear wins in the session facts, set `wins` to an empty list.
- Keep responses brief and action-oriented.
- Do not psychoanalyze.
- Focus only on what actually happened in this session.

Session stats:
- Duration seconds: {elapsed_seconds:.0f}
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- End/Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Extracted session facts:
{session_facts}

Task:
Return ONLY a JSON object matching PatientFeedbackJSON schema with:

- reflection: 1–3 short factual reflections about what happened.
- wins: 0–3 short items. 
  • If there were no real wins in the session facts, return an empty list [].
  • Do NOT invent wins.
- skill_to_practice: one specific ERP skill to focus on next time.
- one_micro_goal_next_time: one very small, concrete exposure step for the next session.
- reminder: optional, one short line encouraging willingness to feel discomfort (not reassurance).

Keep everything concise and grounded strictly in the session facts.
""".strip()