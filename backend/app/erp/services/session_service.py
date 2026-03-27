# app/erp/services/session_service.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.erp.models import ERPItem, ERPLiveSession


class ERPSessionService:
    """
    Handles lifecycle + timer math for ERPLiveSession.

    Your timer model:
      - accumulated_seconds: total time already counted (from previous running segments)
      - resumed_at: timestamp when the current running segment started
      - status: running | paused | ending | ended

    The frontend display time is:
      if running: accumulated_seconds + (now - resumed_at)
      else: accumulated_seconds
    """

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # Session lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def start_session(self, *, erp_item_id: int, patient_id: int) -> ERPLiveSession:
        """
        Creates a new running session for an ERP item.

        Notes:
        - We do NOT auto-close previous sessions here; keep it explicit.
          (You can enforce "only one running session" at API layer if you want.)
        """
        item = self._require_item(erp_item_id, patient_id)

        now = datetime.utcnow()
        session = ERPLiveSession(
            erp_item_id=item.id,
            patient_id=patient_id,
            status="running",
            accumulated_seconds=0.0,
            resumed_at=now,
            ended_at=None,
            last_checkin_at=None,
            last_agent_run_at=None,
            last_suds_at=None,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def pause_session(self, *, session_id: int, patient_id: int) -> ERPLiveSession:
        """
        Pauses a running session:
          - adds elapsed segment time into accumulated_seconds
          - clears resumed_at
          - sets status=paused
        """
        session = self._require_session(session_id, patient_id)

        if session.status != "running":
            return session  # no-op

        now = datetime.utcnow()
        session.accumulated_seconds = self._compute_elapsed_seconds(session, now)
        session.resumed_at = None
        session.status = "paused"

        self.db.commit()
        self.db.refresh(session)
        return session

    def resume_session(self, *, session_id: int, patient_id: int) -> ERPLiveSession:
        """
        Resumes a paused session:
          - sets resumed_at=now
          - status=running
        """
        session = self._require_session(session_id, patient_id)

        if session.status != "paused":
            return session  # no-op

        now = datetime.utcnow()
        session.resumed_at = now
        session.status = "running"

        self.db.commit()
        self.db.refresh(session)
        return session

    def end_clicked(self, *, session_id: int, patient_id: int) -> ERPLiveSession:
        """
        Called when user clicks "End Session" (Option A).

        We stop the timer immediately and set status=ending.
        Then your LangGraph returns a debrief prompt and the UI shows a debrief form.

        IMPORTANT:
        - Scheduler should NOT send check-ins to sessions in status 'ending'.
        """
        session = self._require_session(session_id, patient_id)

        now = datetime.utcnow()

        # Stop timer (if it was running)
        if session.status == "running":
            session.accumulated_seconds = self._compute_elapsed_seconds(session, now)
            session.resumed_at = None

        session.status = "ending"
        # Do NOT set ended_at here (ended_at should be set after report saved)
        self.db.commit()
        self.db.refresh(session)
        return session

    def mark_ended(self, *, session_id: int, patient_id: int) -> ERPLiveSession:
        """
        Sets status=ended and ended_at=now. Usually called after reports are saved,
        but you can call it explicitly if needed.
        """
        session = self._require_session(session_id, patient_id)

        now = datetime.utcnow()

        # Stop timer if somehow still running
        if session.status == "running":
            session.accumulated_seconds = self._compute_elapsed_seconds(session, now)
            session.resumed_at = None

        session.status = "ended"
        if session.ended_at is None:
            session.ended_at = now

        self.db.commit()
        self.db.refresh(session)
        return session

    # ──────────────────────────────────────────────────────────────────────────
    # Timer helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_elapsed_seconds(self, *, session_id: int, patient_id: int) -> float:
        """
        Returns the current elapsed seconds according to your timer model.
        Useful if backend needs to validate / compute a SUDS elapsed_seconds fallback.
        """
        session = self._require_session(session_id, patient_id)
        return self._compute_elapsed_seconds(session, datetime.utcnow())

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_elapsed_seconds(self, session: ERPLiveSession, now: datetime) -> float:
        base = float(session.accumulated_seconds or 0.0)

        if session.status == "running" and session.resumed_at is not None:
            delta = (now - session.resumed_at).total_seconds()
            if delta < 0:
                delta = 0.0
            return base + float(delta)

        return base

    def _require_item(self, erp_item_id: int, patient_id: int) -> ERPItem:
        item = (
            self.db.query(ERPItem)
            .filter(ERPItem.id == erp_item_id, ERPItem.patient_id == patient_id)
            .first()
        )
        if not item:
            raise ValueError(f"ERPItem not found for patient: erp_item_id={erp_item_id}, patient_id={patient_id}")
        return item

    def _require_session(self, session_id: int, patient_id: int) -> ERPLiveSession:
        session = (
            self.db.query(ERPLiveSession)
            .filter(ERPLiveSession.id == session_id, ERPLiveSession.patient_id == patient_id)
            .first()
        )
        if not session:
            raise ValueError(f"ERPLiveSession not found for patient: session_id={session_id}, patient_id={patient_id}")
        return session