# app/erp/ERPCoach/nodes/live_intent_router.py
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel
from typing_extensions import Literal as TLiteral

from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.ERPCoach.prompts.router_prompt import build_live_intent_router_prompt


# ✅ The routes our graph can branch to
LiveRoute = Literal[
    "NO_MESSAGE",
    "RATE_REMINDER",
    "SUDS_SPIKE",
    "REASSURANCE_BLOCK",
    "COMPULSION_URGE",
    "AVOIDANCE_QUIT",
    "GENERAL",
]

# ✅ The intent labels the LLM classifier is allowed to output
IntentLabel = TLiteral["REASSURANCE", "COMPULSION_URGE", "AVOIDANCE_QUIT", "GENERAL"]


class LiveIntentOut(BaseModel):
    """Strict structured output for the router LLM call."""
    intent: IntentLabel


def live_intent_router(state: Dict[str, Any]) -> LiveRoute:
    """
    LIVE router using:
      - deterministic priority for CHECK_IN (cooldown/spike/reminder)
      - LLM classifier (router_prompt.py) for USER_MESSAGE intent routing

    Priority order:
      CHECK_IN:
        1) spike_flag + cooldown_ok  -> SUDS_SPIKE    (bypasses engagement — clinical urgency)
        2) recently_engaged          -> NO_MESSAGE     (suppress all non-spike check-ins during active chat)
        3) not cooldown_ok           -> NO_MESSAGE     (anti-spam)
        4) rate_reminder_flag        -> RATE_REMINDER  (fires only when patient is idle)
        5) otherwise                 -> NO_MESSAGE

      USER_MESSAGE:
        1) if empty -> GENERAL
        2) call LLM classifier -> map to handler route
        3) if classifier fails -> GENERAL (safe fallback)
    """
    event_type = (state.get("event_type") or "").strip().upper()

    # ── SUDS_SUBMITTED: only purpose is immediate spike detection ──────────────
    # Fired by the SUDS endpoint right after saving a new reading.
    # Does nothing except send a spike alert (if warranted); Celery handles
    # all periodic reminders.
    if event_type == "SUDS_SUBMITTED":
        if bool(state.get("spike_flag", False)):
            return "SUDS_SPIKE"
        return "NO_MESSAGE"

    # ── CHECK_IN routing is deterministic (never LLM-decided) ──────────────────
    if event_type == "CHECK_IN":
        cooldown_ok = bool(state.get("cooldown_ok", True))
        spike_flag = bool(state.get("spike_flag", False))
        rate_reminder_flag = bool(state.get("rate_reminder_flag", False))
        recently_engaged = bool(state.get("recently_engaged", False))
        since_last_suds: Optional[float] = state.get("since_last_suds_seconds")

        # SUDS spike is clinically urgent — fire even while the patient is
        # actively chatting, but still respect the cooldown so we don't spam.
        # However, if SUDS was submitted very recently (<30 s), the SUDS
        # endpoint's own graph call (SUDS_SUBMITTED) is handling the spike;
        # skip it here to prevent double messages.
        SUDS_SPIKE_LOCKOUT_SECONDS = 30.0
        if spike_flag and cooldown_ok:
            if since_last_suds is None or since_last_suds >= SUDS_SPIKE_LOCKOUT_SECONDS:
                return "SUDS_SPIKE"
            # else: fall through — SUDS endpoint is (or was just) handling it

        # Patient is active (sent a message or rated SUDS within engagement_window).
        # Suppress all remaining auto check-ins — don't interrupt an active chat.
        if recently_engaged:
            return "NO_MESSAGE"

        # Patient is idle. Respect cooldown before sending anything.
        if not cooldown_ok:
            return "NO_MESSAGE"

        # Patient has been idle long enough — send a SUDS rate reminder if due.
        if rate_reminder_flag:
            return "RATE_REMINDER"

        return "NO_MESSAGE"

    # ── USER_MESSAGE routing uses router_prompt + LLM structured output ─────────
    user_message = (state.get("user_message") or "").strip()
    if not user_message:
        return "GENERAL"

    obsession = state.get("obsession", "") or ""
    compulsions = state.get("compulsions", []) or []
    transcript_tail = state.get("transcript_block", "") or ""

    # LLM client must be injected into state by graph setup OR you can create here.
    # Best practice: graph injects llm into state or passes via partial.
    llm: Optional[LLMClient] = state.get("llm_client")
    if llm is None:
        # Safe fallback: avoid crashing router; default to GENERAL.
        return "GENERAL"

    prompt = build_live_intent_router_prompt(
        obsession=obsession,
        compulsions=compulsions,
        user_message=user_message,
        transcript_tail=transcript_tail[-1500:],  # keep tail small
    )

    try:
        out = llm.structured_call(
            schema=LiveIntentOut,
            prompt=prompt,
            # router should be cheap and consistent
            attempts=2,
            repair_attempts=0,
        )
        intent = out.intent
    except Exception:
        return "GENERAL"

    if intent == "REASSURANCE":
        return "REASSURANCE_BLOCK"
    if intent == "COMPULSION_URGE":
        return "COMPULSION_URGE"
    if intent == "AVOIDANCE_QUIT":
        return "AVOIDANCE_QUIT"
    return "GENERAL"