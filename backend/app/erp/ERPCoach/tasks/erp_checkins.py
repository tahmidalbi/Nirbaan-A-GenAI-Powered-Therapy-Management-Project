# app/erp/tasks/erp_checkins.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.erp.services.coach_storage import CoachStorage
from app.erp.models import ERPLiveSession

# Beat schedule is defined in app/core/celery_app.py — do not set it here.

# TODO: change back to 300 (5 min) for production
CHECKIN_SECONDS = 120  # 2 minutes


def _get_db() -> Session:
    return SessionLocal()


def _get_erp_coach_graph():
    """
    You must implement this function somewhere stable, e.g.
    app/erp/ERPCoach/graph.py exposing:
        def get_erp_coach_graph(): return compiled_graph

    Then import it here.
    """
    from app.erp.ERPCoach.graph import get_erp_coach_graph  # type: ignore

    return get_erp_coach_graph()


@celery_app.task(name="app.erp.ERPCoach.tasks.erp_checkins.dispatch_due_checkins")
def dispatch_due_checkins() -> dict:
    """
    Runs every minute.
    Finds running sessions whose last_checkin_at is >= 5 minutes ago (or NULL),
    then enqueues run_checkin(session_id) per session.

    This keeps scheduling deterministic and cheap.
    """
    db = _get_db()
    try:
        storage = CoachStorage(db)

        due_session_ids = storage.find_running_sessions_due_for_checkin(
            checkin_seconds=CHECKIN_SECONDS,
            limit=500,
        )

        enqueued = 0
        for session_id in due_session_ids:
            run_checkin.delay(session_id)
            enqueued += 1

        return {"ok": True, "due": len(due_session_ids), "enqueued": enqueued}
    finally:
        db.close()


@celery_app.task(name="app.erp.ERPCoach.tasks.erp_checkins.run_checkin")
def run_checkin(session_id: int) -> dict:
    """
    For a single session:
      - Skip if session not running (important!)
      - Call LangGraph with event_type=CHECK_IN
      - If response is NO_MESSAGE, do nothing (but update last_checkin_at to avoid spam loops)
      - Else store coach message into ERPChatMessage and return
    """
    db = _get_db()
    try:
        # Load session quickly to check status
        session: Optional[ERPLiveSession] = (
            db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
        )
        if not session:
            return {"ok": False, "error": "session_not_found", "session_id": session_id}

        # Only check-in for running sessions
        if session.status != "running":
            return {"ok": True, "skipped": True, "reason": f"status={session.status}", "session_id": session_id}

        storage = CoachStorage(db)

        # Mark last_checkin_at immediately (prevents duplicate check-ins if tasks overlap)
        storage.update_last_checkin_at(session_id, when=datetime.utcnow(), commit=True)

        # Use invoke_erp_coach() so storage/llm_client/db are injected properly
        from app.erp.ERPCoach.graph import invoke_erp_coach
        result = invoke_erp_coach(
            {
                "session_id": session_id,
                "event_type": "CHECK_IN",
                "user_message": "",
            }
        )

        # result should include a CoachResponse-like dict under "coach_response_json"
        coach_resp = result.get("coach_response_json") or result.get("response") or result

        # If graph decides NO_MESSAGE, stop here.
        # last_agent_run_at is NOT updated — no real message was sent, so the
        # cooldown timer should not reset.
        if not coach_resp or coach_resp.get("type") == "NO_MESSAGE":
            return {"ok": True, "session_id": session_id, "type": "NO_MESSAGE"}

        # NOTE: The graph's log_coach node already persisted the message AND
        # updated last_agent_run_at (via persist.log_coach_message).
        # No further writes needed here.

        return {"ok": True, "session_id": session_id, "type": coach_resp.get("type", "COACH_MESSAGE")}
    finally:
        db.close()