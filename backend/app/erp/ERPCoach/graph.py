# app/erp/ERPCoach/graph.py
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.database.session import SessionLocal
from app.erp.ERPCoach.state import CoachState
from app.erp.ERPCoach.events import normalize_event_type

from app.erp.services.coach_storage import CoachStorage
from app.erp.ERPCoach.llm.client import LLMClient

# Nodes
from app.erp.ERPCoach.nodes.load_context import load_context_node
from app.erp.ERPCoach.nodes.compute_metrics import compute_metrics_node
from app.erp.ERPCoach.nodes.mode_router import mode_router
from app.erp.ERPCoach.nodes.live_intent_router import live_intent_router

from app.erp.ERPCoach.nodes.live_handlers import (
    handle_general,
    handle_reassurance_block,
    handle_compulsion_urge,
    handle_avoidance_quit,
    handle_rate_reminder,
    handle_suds_spike,
    handle_no_message,
)

from app.erp.ERPCoach.nodes.debrief_prompt import send_debrief_prompt

from app.erp.ERPCoach.nodes.report_bundle import assemble_report_bundle
from app.erp.ERPCoach.nodes.report_generate import (
    compress_session_facts,
    generate_therapist_report,
    generate_patient_feedback,
)

from app.erp.ERPCoach.nodes.finalize_json import (
    finalize_coach_response,
    finalize_reports,
)

from app.erp.ERPCoach.nodes.persist import (
    log_user_message,
    log_coach_message,
    log_debrief_prompt,
    save_reports_update_latest,
)


# ──────────────────────────────────────────────────────────────────────────────
# Adapters (deps come from state)
# ──────────────────────────────────────────────────────────────────────────────

def _storage(state: Dict[str, Any]) -> CoachStorage:
    s = state.get("storage")
    if s is None:
        raise RuntimeError("storage missing from state. invoke_erp_coach must inject it.")
    return s

def _llm(state: Dict[str, Any]) -> LLMClient:
    l = state.get("llm_client")
    if l is None:
        raise RuntimeError("llm_client missing from state. invoke_erp_coach must inject it.")
    return l


def _node_load_context(state: Dict[str, Any]) -> Dict[str, Any]:
    return load_context_node(state)  # uses storage already injected in state

def _node_compute_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    return compute_metrics_node(state)

def _node_log_user(state: Dict[str, Any]) -> Dict[str, Any]:
    return log_user_message(state, storage=_storage(state))

def _node_log_coach(state: Dict[str, Any]) -> Dict[str, Any]:
    return log_coach_message(state, storage=_storage(state))

def _node_log_debrief_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    return log_debrief_prompt(state, storage=_storage(state))

def _node_save_reports(state: Dict[str, Any]) -> Dict[str, Any]:
    return save_reports_update_latest(state, storage=_storage(state))


# LIVE handlers (need llm)
def _node_general(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_general(state, llm=_llm(state))

def _node_reassurance(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_reassurance_block(state, llm=_llm(state))

def _node_urge(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_compulsion_urge(state, llm=_llm(state))

def _node_quit(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_avoidance_quit(state, llm=_llm(state))

def _node_rate_reminder(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_rate_reminder(state, llm=_llm(state))

def _node_spike(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_suds_spike(state, llm=_llm(state))

def _node_no_message(state: Dict[str, Any]) -> Dict[str, Any]:
    return handle_no_message(state, llm=_llm(state))


# DEBRIEF
def _node_debrief_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    return send_debrief_prompt(state, llm=_llm(state))


# REPORT
def _node_report_bundle(state: Dict[str, Any]) -> Dict[str, Any]:
    return assemble_report_bundle(state)

def _node_facts(state: Dict[str, Any]) -> Dict[str, Any]:
    return compress_session_facts(state, llm=_llm(state))

def _node_therapist_report(state: Dict[str, Any]) -> Dict[str, Any]:
    return generate_therapist_report(state, llm=_llm(state))

def _node_patient_feedback(state: Dict[str, Any]) -> Dict[str, Any]:
    return generate_patient_feedback(state, llm=_llm(state))


# ──────────────────────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_erp_coach_graph():
    g = StateGraph(CoachState)

    # Core
    g.add_node("load_context", _node_load_context)
    g.add_node("compute_metrics", _node_compute_metrics)

    # LIVE
    g.add_node("log_user", _node_log_user)
    g.add_node("live_general", _node_general)
    g.add_node("live_reassurance", _node_reassurance)
    g.add_node("live_urge", _node_urge)
    g.add_node("live_quit", _node_quit)
    g.add_node("live_rate_reminder", _node_rate_reminder)
    g.add_node("live_spike", _node_spike)
    g.add_node("live_no_message", _node_no_message)

    g.add_node("finalize_coach_live", finalize_coach_response)
    g.add_node("log_coach", _node_log_coach)

    # DEBRIEF
    g.add_node("debrief_prompt", _node_debrief_prompt)
    g.add_node("finalize_coach_debrief", finalize_coach_response)
    g.add_node("log_debrief_prompt", _node_log_debrief_prompt)

    # REPORT
    g.add_node("report_bundle", _node_report_bundle)
    g.add_node("report_facts", _node_facts)
    g.add_node("report_therapist", _node_therapist_report)
    g.add_node("report_patient", _node_patient_feedback)
    g.add_node("finalize_reports", finalize_reports)
    g.add_node("save_reports", _node_save_reports)

    # START → load_context → compute_metrics
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "compute_metrics")

    # Mode routing
    g.add_conditional_edges(
        "compute_metrics",
        mode_router,
        {
            "LIVE": "log_user",
            "DEBRIEF_PROMPT": "debrief_prompt",
            "REPORT": "report_bundle",
        },
    )

    # LIVE routing after log_user
    g.add_conditional_edges(
        "log_user",
        live_intent_router,
        {
            "NO_MESSAGE": "live_no_message",
            "RATE_REMINDER": "live_rate_reminder",
            "SUDS_SPIKE": "live_spike",
            "REASSURANCE_BLOCK": "live_reassurance",
            "COMPULSION_URGE": "live_urge",
            "AVOIDANCE_QUIT": "live_quit",
            "GENERAL": "live_general",
        },
    )

    # LIVE: handler → finalize_live → persist → END
    for node in [
        "live_no_message",
        "live_rate_reminder",
        "live_spike",
        "live_reassurance",
        "live_urge",
        "live_quit",
        "live_general",
    ]:
        g.add_edge(node, "finalize_coach_live")

    g.add_edge("finalize_coach_live", "log_coach")
    g.add_edge("log_coach", END)

    # DEBRIEF: prompt → finalize_debrief → persist → END
    g.add_edge("debrief_prompt", "finalize_coach_debrief")
    g.add_edge("finalize_coach_debrief", "log_debrief_prompt")
    g.add_edge("log_debrief_prompt", END)

    # REPORT: bundle → facts → therapist → patient → finalize → save → END
    g.add_edge("report_bundle", "report_facts")
    g.add_edge("report_facts", "report_therapist")
    g.add_edge("report_therapist", "report_patient")
    g.add_edge("report_patient", "finalize_reports")
    g.add_edge("finalize_reports", "save_reports")
    g.add_edge("save_reports", END)

    return g.compile()


def invoke_erp_coach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates db + storage + llm ONCE per invocation, injects into state, and guarantees close.
    """
    payload = dict(payload)
    payload["event_type"] = normalize_event_type(payload.get("event_type"))

    db = SessionLocal()
    try:
        payload["db"] = db
        payload["storage"] = CoachStorage(db)
        payload["llm_client"] = LLMClient()

        graph = get_erp_coach_graph()
        return graph.invoke(payload)

    except Exception:
        # best-effort rollback
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()