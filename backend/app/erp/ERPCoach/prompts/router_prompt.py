# app/erp/ERPCoach/prompts/router_prompt.py
from __future__ import annotations

from typing import List


def build_live_intent_router_prompt(
    *,
    obsession: str,
    compulsions: List[str],
    user_message: str,
    transcript_tail: str,
) -> str:
    """
    Classifies a user message into one of a small set of intents.

    Output MUST be a single word from:
      REASSURANCE
      COMPULSION_URGE
      AVOIDANCE_QUIT
      GENERAL
    """
    compulsions_txt = "\n".join([f"- {c}" for c in (compulsions or [])]) or "- (none)"
    obsession_txt = (obsession or "").strip()[:1200]
    msg = (user_message or "").strip()[:1800]
    tail = (transcript_tail or "").strip()[-1800:]

    return f"""
You are an intent classifier for an OCD ERP coaching app.
Your job is ONLY to label the user's latest message so the correct handler responds.

Important:
- Output EXACTLY ONE word: REASSURANCE, COMPULSION_URGE, AVOIDANCE_QUIT, or GENERAL.
- Do not add punctuation. Do not explain. Do not output JSON.
- Use the user's intent, not your advice.

Definitions (choose the BEST match):
REASSURANCE
- Asking for certainty/safety: “am I okay?”, “promise me…”, “tell me it won’t happen”
- Wanting reassurance about the feared outcome, morality, responsibility, health, or consequences
- “Is this normal?”, “does this mean…?”, “can you confirm…?” (when used to feel certain)

COMPULSION_URGE
- Wants to DO something to reduce anxiety or “make sure” (ritual/safety behavior)
- Examples: checking, washing, googling, confessing, seeking reassurance, repeating, mental reviewing,
  neutralizing, avoiding triggers, asking others, “I need to do it right now”, “should I check again?”

AVOIDANCE_QUIT
- Wants to stop or escape exposure: “I can’t”, “I’m done”, “end this”, “I need to leave”, “too much”
- Requests to end early specifically to escape anxiety/discomfort

GENERAL
- Anything else (status update, describing feelings without asking for certainty, asking how to do ERP steps,
  short questions that aren’t reassurance/ritual urges, practical/logistics).

Context (for disambiguation):
Obsession/fear:
{obsession_txt}

Compulsions list:
{compulsions_txt}

Recent transcript (tail):
{tail or "(none)"}

User message:
{msg}

Return ONLY one word.
""".strip()