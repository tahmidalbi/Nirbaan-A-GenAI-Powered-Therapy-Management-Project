# app/erp/tasks/erp_reports.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.erp.services.coach_storage import CoachStorage
from app.erp.models import ERPLiveSession


def _get_db() -> Session:
    return SessionLocal()


@celery_app.task(name="app.erp.ERPCoach.tasks.erp_reports.run_end_session_report")
def run_end_session_report(session_id: int, patient_debrief_text: str) -> dict:
    """
    Generates the therapist report + patient feedback after the patient submits debrief.

    Expected flow:
      - API receives debrief
      - API stores patient message (optional)
      - API enqueues this task
      - UI polls an endpoint to see when session.therapist_report_json is available

    This task:
      - verifies session exists
      - calls LangGraph with END_SESSION_REPORT + debrief text
      - graph should save reports (or return them so API saves; either way works)
    """
    db = _get_db()
    try:
        session: Optional[ERPLiveSession] = (
            db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
        )
        if not session:
            return {"ok": False, "error": "session_not_found", "session_id": session_id}

        # Use invoke_erp_coach() so storage/llm_client/db are injected properly
        from app.erp.ERPCoach.graph import invoke_erp_coach
        result = invoke_erp_coach(
            {
                "session_id": session_id,
                "event_type": "END_SESSION_REPORT",
                "patient_debrief_text": patient_debrief_text,
            }
        )

        # If your graph returns report json instead of saving, save here.
        therapist_report = result.get("therapist_report_json")
        patient_feedback = result.get("patient_feedback_json")

        if therapist_report is not None and patient_feedback is not None:
            storage = CoachStorage(db)
            storage.save_end_session_reports(
                session_id=session_id,
                patient_debrief_text=patient_debrief_text,
                therapist_report_json=therapist_report,
                patient_feedback_json=patient_feedback,
                commit=True,
            )
            storage.set_item_latest_session(session.erp_item_id, session_id, commit=True)

        return {"ok": True, "session_id": session_id, "saved": True, "at": datetime.utcnow().isoformat()}
    finally:
        db.close()