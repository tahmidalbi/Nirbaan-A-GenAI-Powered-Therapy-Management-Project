# app/erp/ERPCoach/prompts/router_prompt.py
from __future__ import annotations

from typing import List, Optional


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

    return f"""
You are a classifier for an ERP coach. Choose the best intent for the user's message.

Context:
Obsession:
{obsession}

Compulsions list:
{compulsions_txt}

Recent transcript (tail):
{transcript_tail or "(none)"}

User message:
{user_message}

Intents:
- REASSURANCE: seeking certainty, safety confirmation, "is it okay?", "tell me it's not true"
- COMPULSION_URGE: wants to check, wash, confess, seek reassurance, avoid, neutralize, do a ritual
- AVOIDANCE_QUIT: wants to stop, escape, end session, can't do it, wants to avoid trigger
- GENERAL: anything else

Return ONLY the intent word.
""".strip()