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


# ------------------------------------------------------------------
# STEP 1 — Extract factual session bullets
# ------------------------------------------------------------------

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
    Step 1 in report pipeline.

    Convert structured inputs + patient debrief into factual session bullets.
    IMPORTANT:
    - Do NOT summarize the AI coach behavior.
    - Base conclusions primarily on the patient's debrief and SUDS pattern.
    """

    return f"""
You are assisting a therapist by extracting structured factual notes from an ERP exposure session.

Strict rules:
- Do NOT summarize or reference the AI coach.
- Use ONLY: obsession, compulsions list, exercise note, SUDS points, and patient debrief.
- Transcript is secondary context only if the debrief is unclear.
- Be factual, neutral, and concise.
- Do NOT psychoanalyze or reassure.

Context:

Obsession target:
{_clip(obsession, 1200)}

Compulsions / safety behaviors to prevent:
{_bullet(compulsions, 12)}

Planned exercise note:
{_clip(exercise_text, 1200) if exercise_text else "(none provided)"}

SUDS series (elapsed_seconds -> value):
{suds_points_block or "(no SUDS readings)"}

Patient debrief (primary narrative):
{_clip(patient_debrief_text, 2400)}

Prior session summaries (continuity only):
{_bullet(prior_summaries, 3)}

Transcript (secondary context):
{transcript_block or "(none)"}

Task:
Produce factual bullets under the following sections:

- Exposure task attempted
- Triggers or moments of distress
- Compulsions / urges (resisted vs performed)
- Avoidance / safety behaviors
- Patient-reported observations or reflections
- SUDS pattern observations

Rules:
- Prefer patient language from the debrief.
- If something is unclear, mark it as "unclear".
- Do not infer therapy conclusions.
- Maximum ~20 bullets total.
""".strip()


# ------------------------------------------------------------------
# STEP 2 — Therapist-facing clinical report
# ------------------------------------------------------------------

def build_therapist_report_prompt(
    *,
    session_facts: str,
    elapsed_seconds: float,
    suds_peak: Optional[int],
    suds_latest: Optional[int],
    prior_reports_block: str = "",
) -> str:
    """
    Generate therapist-facing ERP report JSON.
    """

    cross_session_instruction = ""
    if prior_reports_block.strip():
        cross_session_instruction = f"""
Prior session data (for cross-session analysis):
{prior_reports_block}

cross_session_overview:
  Analyze the prior sessions above together with this session.
  Return a JSON object with these keys:
  {{
    "summary": "2-3 sentence clinical narrative across all sessions combined",
    "common_patterns": ["recurring themes, triggers, or behaviors across sessions"],
    "blockers_to_progress": ["factors repeatedly preventing improvement or habituation"],
    "progress_signs": ["areas showing improvement across sessions compared to earlier ones"]
  }}
  Rules:
  - Only include items clearly supported by the prior session data.
  - If a list has no evidence, return an empty list [].
  - "blockers_to_progress" is the most important — always complete it if any pattern of stuck behavior exists.
"""
    else:
        cross_session_instruction = """
cross_session_overview:
  null  (no prior session data available for cross-session analysis)
"""

    return f"""
You are generating a therapist-facing ERP session report as STRICT JSON.

Clinical style:
- Professional, concise, and behaviorally descriptive.
- Do NOT reference an AI system.
- Do NOT invent details.

Use ONLY:
- session_facts
- session stats
- prior session data (if provided)

Session stats:
- Duration seconds: {elapsed_seconds:.0f}
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- End/Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Session facts:
{session_facts}

CRITICAL RULE — Key Learning:
- Only include entries in key_learning if the patient explicitly described an insight.
- Statements like "it was hard" or "I gave in" are NOT learning.
- If no learning is clearly present, return an empty list [].

Return ONLY a JSON object matching TherapistReportJSON with:

session_overview:
  Include:
  - duration_minutes
  - peak_suds
  - end_suds
  - exposure_target (short phrase)

suds_curve_summary:
  1–2 clinical sentences describing the pattern of anxiety during the session.

what_happened:
  3–8 bullets describing exposure actions and key events.

compulsions_urges:
  List urges or rituals reported.

response_prevention_successes:
  Attempts at resisting or delaying compulsions.

avoidance_or_safety_behaviors:
  Behaviors that reduced exposure intensity.

key_learning:
  Only real patient takeaways or insights.

recommend_next_step:
  Provide a structured suggestion with keys:
  {{
    "focus": "...",
    "rationale": "...",
    "suggested_next_exposure": "...",
    "response_prevention_plan": "..."
  }}

risk_flags:
  Usually empty. Only include if facts clearly indicate risk.
{cross_session_instruction}
""".strip()


# ------------------------------------------------------------------
# CROSS-SESSION OVERVIEW — standalone prompt for patching old reports
# ------------------------------------------------------------------

def build_cross_session_overview_prompt(
    *,
    current_session_block: str,
    prior_reports_block: str,
) -> str:
    """
    Single-purpose prompt that generates only cross_session_overview.
    Called when backfilling existing reports that predate the feature.
    """
    return f"""
You are generating a cross-session clinical overview for a therapist working with an OCD patient doing ERP (Exposure and Response Prevention) therapy.

Strict rules:
- Do NOT reference an AI system.
- Do NOT invent details not present in the session data.
- Be clinically precise and concise.

Current session:
{current_session_block}

Prior sessions:
{prior_reports_block}

Task:
Return ONLY a JSON object with these four keys:

summary:
  2-3 sentence clinical narrative synthesizing patterns across ALL sessions combined.

common_patterns:
  List of recurring themes, triggers, or behaviors that appear consistently across multiple sessions.
  Only include items clearly present in 2 or more sessions.

blockers_to_progress:
  List of factors that repeatedly prevent improvement or habituation.
  This is the most important field — include anything that keeps appearing as a barrier
  (e.g., consistent compulsion performance, avoidance, reassurance-seeking, short duration, same trigger).
  If a list has no evidence, return an empty list [].

progress_signs:
  List of areas where improvement is visible comparing earlier sessions to more recent ones.
  Only include if genuinely supported by the data. If none, return [].
""".strip()


# ------------------------------------------------------------------
# STEP 3 — Patient-facing feedback
# ------------------------------------------------------------------

def build_patient_feedback_prompt(
    *,
    session_facts: str,
    elapsed_seconds: float,
    suds_peak: Optional[int],
    suds_latest: Optional[int],
) -> str:
    """
    Generate patient-facing ERP feedback JSON.

    Tone: therapist-like, supportive, professional.
    """

    return f"""
You are generating patient-facing ERP feedback as STRICT JSON.

Tone:
- Warm, supportive, therapist-like.
- Encouraging without reassurance.
- Do NOT say the feared outcome is impossible or safe.

Evidence rule:
- Base everything strictly on session_facts.
- Do NOT invent wins.

Session stats:
- Duration seconds: {elapsed_seconds:.0f}
- Peak SUDS: {suds_peak if suds_peak is not None else "NA"}
- End/Latest SUDS: {suds_latest if suds_latest is not None else "NA"}

Session facts:
{session_facts}

Return ONLY JSON matching PatientFeedbackJSON.

reflection:
- 2–4 brief reflections summarizing what they practiced or experienced.

wins:
- Only include wins clearly supported by facts.
- If none exist, return [].

skill_to_practice:
Choose ONE ERP skill relevant to this session such as:
- response prevention through delay
- willingness toward uncertainty
- reducing rumination
- urge surfing
- dropping safety behaviors

one_micro_goal_next_time:
Provide a practical next step for the next session.

Important:
- Do NOT write rigid instructions like "do this for 60 seconds".
- Write like a therapist-assistant plan

reminder:
Optional short therapist-assistant-style reminder emphasizing willingness rather than anxiety reduction.
Example:
"Progress comes from practicing a new response, not from making anxiety disappear."
""".strip()