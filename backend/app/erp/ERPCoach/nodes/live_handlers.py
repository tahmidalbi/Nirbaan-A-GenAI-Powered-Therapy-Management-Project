# app/erp/ERPCoach/nodes/live_handlers.py
from __future__ import annotations

from typing import Any, Dict

from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.schemas import CoachResponse

from app.erp.ERPCoach.prompts.live_handlers import (
    prompt_general_coaching,
    prompt_reassurance_block,
    prompt_compulsion_urge,
    prompt_avoidance_or_quit,
    prompt_checkin_general,
    prompt_rate_reminder,
    prompt_suds_spike,
)


def _ctx(state: Dict[str, Any]) -> Dict[str, Any]:
    """Small helper to pull common context fields from state."""
    return {
        "obsession": state.get("obsession", ""),
        "compulsions": state.get("compulsions", []) or [],
        "exercise_text": state.get("exercise_text"),
        "elapsed_seconds": float(state.get("elapsed_seconds", 0.0)),
        "suds_latest": state.get("suds_latest"),
        "suds_peak": state.get("suds_peak"),
        "suds_trend_hint": state.get("suds_trend_hint"),
        "prior_summaries": state.get("prior_summaries", []) or [],
        "transcript_block": state.get("transcript_block", "") or "",
        # ✅ NEW: give prompts deterministic “don’t over-ask” signals
        "since_last_suds_seconds": state.get("since_last_suds_seconds"),
        "since_last_agent_seconds": state.get("since_last_agent_seconds"),
        "rate_reminder_flag": bool(state.get("rate_reminder_flag", False)),
        "spike_flag": bool(state.get("spike_flag", False)),
        "cooldown_ok": bool(state.get("cooldown_ok", True)),
    }


def handle_general(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    LIVE handler for general coaching.
    Used for USER_MESSAGE and CHECK_IN (general check-in).
    """
    ctx = _ctx(state)
    event_type = (state.get("event_type") or "").strip().upper()
    user_message = state.get("user_message", "")

    if event_type == "CHECK_IN":
        prompt = prompt_checkin_general(**ctx)
    else:
        prompt = prompt_general_coaching(**ctx, user_message=user_message)

    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state


def handle_reassurance_block(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """USER_MESSAGE handler for reassurance-seeking."""
    ctx = _ctx(state)
    prompt = prompt_reassurance_block(**ctx, user_message=state.get("user_message", ""))
    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state


def handle_compulsion_urge(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """USER_MESSAGE handler for compulsion urge."""
    ctx = _ctx(state)
    prompt = prompt_compulsion_urge(**ctx, user_message=state.get("user_message", ""))
    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state


def handle_avoidance_quit(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """USER_MESSAGE handler when patient wants to stop/avoid/end early."""
    ctx = _ctx(state)
    prompt = prompt_avoidance_or_quit(**ctx, user_message=state.get("user_message", ""))
    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state


def handle_rate_reminder(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """CHECK_IN handler: remind to rate SUDS."""
    ctx = _ctx(state)
    prompt = prompt_rate_reminder(**ctx)
    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state


def handle_suds_spike(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """CHECK_IN handler: SUDS spike stabilization message."""
    ctx = _ctx(state)
    prompt = prompt_suds_spike(**ctx)
    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    # ✅ Optional: helps you de-dupe spikes later if you implement it in compute_metrics
    state["spike_notified_suds"] = state.get("suds_latest")
    return state


def handle_no_message(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    CHECK_IN handler when cooldown says don't speak.
    Returns a static NO_MESSAGE response — no LLM call needed.
    """
    static_json = {
        "type": "NO_MESSAGE",
        "source": "CHECK_IN",
        "coach_message": None,
        "next_action": {"type": "NONE", "payload": {}},
        "tags": ["cooldown_no_message"],
    }
    resp = CoachResponse.model_validate(static_json)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state