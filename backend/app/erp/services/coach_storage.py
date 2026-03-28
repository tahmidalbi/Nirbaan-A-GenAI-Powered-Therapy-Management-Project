# app/erp/services/coach_storage.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.erp.models import (
    ERPItem,
    ERPLiveSession,
    ERPSUDSReading,
    ERPChatMessage,
    ERPExerciseNote,
)


@dataclass
class SessionBundle:
    """Everything the LangGraph coach needs to make a decision for one run."""
    session: ERPLiveSession
    item: ERPItem

    obsession: str
    compulsions: List[str]

    # Latest exercise note content (patient-written for this session/item)
    exercise_text: Optional[str]

    # Chat transcript tail (continuity inside the session)
    messages: List[ERPChatMessage]

    # SUDS continuity
    suds_recent: List[ERPSUDSReading]
    suds_peak: Optional[int]
    last_suds_at: Optional[datetime]

    # Continuity across sessions for same obsession item
    latest_report_session: Optional[ERPLiveSession]
    prior_sessions: List[ERPLiveSession]  # recent ended sessions for same item (excluding current)

    # Handy "compact summaries" (optional but useful)
    prior_session_summaries: List[str]


class CoachStorage:
    """
    DB adapter for the ERP Coach system.

    LangGraph nodes should NOT do complex SQL. They call these methods.
    This keeps:
      - DB queries in one place
      - consistency (same limits/ordering everywhere)
      - easy testing (can mock CoachStorage)
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Core "bundle" fetch used by load_context node
    # -------------------------------------------------------------------------
    def get_session_bundle(
        self,
        session_id: int,
        *,
        message_limit: int = 20,
        suds_limit: int = 12,
        prior_sessions_limit: int = 3,
        include_transcript: bool = True,
    ) -> SessionBundle:
        """
        Fetch everything needed for:
          - live coaching (USER_MESSAGE / CHECK_IN)
          - debrief prompt
          - end-session report generation

        Returns a SessionBundle that LangGraph can convert into its state.
        """
        session = self._require_session(session_id)
        item = self._require_item(session.erp_item_id)

        obsession = item.obsession
        compulsions = list(item.compulsions or [])

        exercise_text = self.get_latest_exercise_note_text(item.id, session.patient_id)

        messages: List[ERPChatMessage] = []
        if include_transcript:
            messages = (
                self.db.query(ERPChatMessage)
                .filter(ERPChatMessage.session_id == session_id)
                .order_by(desc(ERPChatMessage.created_at))
                .limit(message_limit)
                .all()
            )
            # Return in chronological order (oldest -> newest)
            messages = list(reversed(messages))

        suds_recent = (
            self.db.query(ERPSUDSReading)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.recorded_at))
            .limit(suds_limit)
            .all()
        )
        suds_recent = list(reversed(suds_recent))  # chronological order

        suds_peak = self.get_session_peak_suds(session_id)
        last_suds_at = self.get_last_suds_at(session_id)

        latest_report_session = self.get_latest_report_session_for_item(item.id)

        prior_sessions = self.get_recent_ended_sessions_for_item(
            item.id,
            exclude_session_id=session_id,
            limit=prior_sessions_limit,
        )

        prior_session_summaries = []
        for s in prior_sessions:
            prior_session_summaries.append(self._compact_session_summary(s))

        return SessionBundle(
            session=session,
            item=item,
            obsession=obsession,
            compulsions=compulsions,
            exercise_text=exercise_text,
            messages=messages,
            suds_recent=suds_recent,
            suds_peak=suds_peak,
            last_suds_at=last_suds_at,
            latest_report_session=latest_report_session,
            prior_sessions=prior_sessions,
            prior_session_summaries=prior_session_summaries,
        )

    # -------------------------------------------------------------------------
    # Writes: chat messages, status updates, reports, latest pointers
    # -------------------------------------------------------------------------
    def save_chat_message(
        self,
        *,
        session_id: int,
        erp_item_id: int,
        patient_id: int,
        role: str,  # "patient" | "coach" | "system"
        content: str,
        intent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        commit: bool = True,
    ) -> ERPChatMessage:
        msg = ERPChatMessage(
            session_id=session_id,
            erp_item_id=erp_item_id,
            patient_id=patient_id,
            role=role,
            content=content,
            intent=intent,
            tags=tags or [],
            created_at=created_at or datetime.utcnow(),
        )
        self.db.add(msg)
        if commit:
            self.db.commit()
            self.db.refresh(msg)
        return msg

    def set_session_status(
        self,
        session_id: int,
        status: str,  # running | paused | ending | ended
        *,
        resumed_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        commit: bool = True,
    ) -> ERPLiveSession:
        session = self._require_session(session_id)
        session.status = status
        if resumed_at is not None:
            session.resumed_at = resumed_at
        if ended_at is not None:
            session.ended_at = ended_at
        if commit:
            self.db.commit()
            self.db.refresh(session)
        return session

    def update_last_checkin_at(self, session_id: int, when: Optional[datetime] = None, *, commit: bool = True) -> None:
        session = self._require_session(session_id)
        session.last_checkin_at = when or datetime.utcnow()
        if commit:
            self.db.commit()

    def update_last_agent_run_at(self, session_id: int, when: Optional[datetime] = None, *, commit: bool = True) -> None:
        session = self._require_session(session_id)
        session.last_agent_run_at = when or datetime.utcnow()
        if commit:
            self.db.commit()

    def update_last_suds_at(self, session_id: int, when: Optional[datetime] = None, *, commit: bool = True) -> None:
        session = self._require_session(session_id)
        session.last_suds_at = when or datetime.utcnow()
        if commit:
            self.db.commit()

    def update_last_spike_notified_suds(self, session_id: int, suds_value: int, *, commit: bool = True) -> None:
        """
        Record the SUDS value at which we last sent a spike notification.
        Prevents the same spike from triggering a second message.
        """
        session = self._require_session(session_id)
        session.last_spike_notified_suds = int(suds_value)
        if commit:
            self.db.commit()

    def get_last_patient_message_at(self, session_id: int) -> Optional[datetime]:
        """
        Returns the timestamp of the most recent message sent by the patient
        (role='patient') in this session, or None if the patient hasn't sent one.
        """
        row = (
            self.db.query(ERPChatMessage.created_at)
            .filter(
                ERPChatMessage.session_id == session_id,
                ERPChatMessage.role == "patient",
            )
            .order_by(desc(ERPChatMessage.created_at))
            .first()
        )
        return row[0] if row else None

    def get_last_therapy_session(self, patient_id: int) -> Optional[str]:
        """
        Returns a formatted string of the patient's most recent therapy session
        (session number, title, date, and transcript), or None if not found.
        therapist_notes are intentionally excluded.
        """
        from app.therapy_sessions.models import TherapySession
        session = (
            self.db.query(TherapySession)
            .filter(TherapySession.patient_id == patient_id)
            .order_by(TherapySession.session_date.desc(), TherapySession.id.desc())
            .first()
        )
        if not session:
            return None
        return (
            f"Session {session.session_number} — {session.title} ({session.session_date})\n"
            f"{(session.transcript or '').strip()}"
        )

    def save_end_session_reports(
        self,
        *,
        session_id: int,
        patient_debrief_text: str,
        therapist_report_json: Dict[str, Any],
        patient_feedback_json: Dict[str, Any],
        commit: bool = True,
    ) -> ERPLiveSession:
        """
        Saves final report blocks onto the session record.
        Also increments report_version so you can re-generate if needed.
        """
        session = self._require_session(session_id)
        session.patient_debrief_text = patient_debrief_text
        session.therapist_report_json = therapist_report_json
        session.patient_feedback_json = patient_feedback_json
        session.report_version = (session.report_version or 0) + 1

        # When report is saved we consider session ended (your flow).
        if session.status != "ended":
            session.status = "ended"
        if session.ended_at is None:
            session.ended_at = datetime.utcnow()
        session.resumed_at = None  # timer stopped

        if commit:
            self.db.commit()
            self.db.refresh(session)
        return session

    def set_item_latest_session(self, erp_item_id: int, session_id: int, *, commit: bool = True) -> ERPItem:
        """
        Updates the ERP item so therapist/patient UI can always show the latest report
        under that obsession item.
        """
        item = self._require_item(erp_item_id)
        item.latest_session_id = session_id
        if commit:
            self.db.commit()
            self.db.refresh(item)
        return item

    # -------------------------------------------------------------------------
    # Reads: latest report, prior sessions, exercise note, SUDS stats
    # -------------------------------------------------------------------------
    def get_latest_exercise_note_text(self, erp_item_id: int, patient_id: int) -> Optional[str]:
        note = (
            self.db.query(ERPExerciseNote)
            .filter(
                ERPExerciseNote.erp_item_id == erp_item_id,
                ERPExerciseNote.patient_id == patient_id,
            )
            .order_by(desc(ERPExerciseNote.created_at))
            .first()
        )
        return note.content if note else None

    def get_last_suds_at(self, session_id: int) -> Optional[datetime]:
        row = (
            self.db.query(ERPSUDSReading.recorded_at)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.recorded_at))
            .first()
        )
        return row[0] if row else None

    def get_session_peak_suds(self, session_id: int) -> Optional[int]:
        # Lightweight peak computation without scanning entire DB in python
        row = (
            self.db.query(ERPSUDSReading.suds_value)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.suds_value))
            .first()
        )
        return int(row[0]) if row else None

    def get_latest_report_session_for_item(self, erp_item_id: int) -> Optional[ERPLiveSession]:
        """
        First try the ERPItem.latest_session_id pointer.
        If not set, fall back to most recent ended session with a report.
        """
        item = self._require_item(erp_item_id)
        if item.latest_session_id:
            return (
                self.db.query(ERPLiveSession)
                .filter(ERPLiveSession.id == item.latest_session_id)
                .first()
            )

        # fallback: most recent ended session with report json present
        return (
            self.db.query(ERPLiveSession)
            .filter(
                ERPLiveSession.erp_item_id == erp_item_id,
                ERPLiveSession.status == "ended",
                ERPLiveSession.therapist_report_json.isnot(None),
            )
            .order_by(desc(ERPLiveSession.ended_at), desc(ERPLiveSession.created_at))
            .first()
        )

    def get_recent_ended_sessions_for_item(
        self,
        erp_item_id: int,
        *,
        exclude_session_id: Optional[int] = None,
        limit: int = 3,
    ) -> List[ERPLiveSession]:
        q = (
            self.db.query(ERPLiveSession)
            .filter(
                ERPLiveSession.erp_item_id == erp_item_id,
                ERPLiveSession.status == "ended",
            )
            .order_by(desc(ERPLiveSession.ended_at), desc(ERPLiveSession.created_at))
        )
        if exclude_session_id is not None:
            q = q.filter(ERPLiveSession.id != exclude_session_id)

        return q.limit(limit).all()

    # -------------------------------------------------------------------------
    # Check-in helper query for Celery beat: find sessions due for check-in
    # -------------------------------------------------------------------------
    def find_running_sessions_due_for_checkin(
        self,
        *,
        checkin_seconds: int = 300,
        limit: int = 200,
    ) -> List[int]:
        """
        Returns a list of session_ids that are:
          - status == running
          - and (last_checkin_at is null OR last_checkin_at older than checkin_seconds)
        """
        cutoff = datetime.utcnow() - timedelta(seconds=checkin_seconds)

        sessions = (
            self.db.query(ERPLiveSession.id)
            .filter(
                ERPLiveSession.status == "running",
                # due if last_checkin_at is null OR last_checkin_at <= cutoff
                (ERPLiveSession.last_checkin_at.is_(None)) | (ERPLiveSession.last_checkin_at <= cutoff),
            )
            .order_by(ERPLiveSession.created_at.asc())
            .limit(limit)
            .all()
        )
        return [int(s[0]) for s in sessions]

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------
    def _require_session(self, session_id: int) -> ERPLiveSession:
        session = self.db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
        if not session:
            raise ValueError(f"ERPLiveSession not found: session_id={session_id}")
        return session

    def _require_item(self, erp_item_id: int) -> ERPItem:
        item = self.db.query(ERPItem).filter(ERPItem.id == erp_item_id).first()
        if not item:
            raise ValueError(f"ERPItem not found: erp_item_id={erp_item_id}")
        return item

    def _compact_session_summary(self, s: ERPLiveSession) -> str:
        """
        Creates a short summary string for continuity.
        This is NOT an LLM summary; it's a compact deterministic summary.
        """
        peak = None
        end_suds = None

        # peak from stored reading query (cheap)
        peak = self.get_session_peak_suds(s.id)

        # end suds: last reading
        last_row = (
            self.db.query(ERPSUDSReading.suds_value, ERPSUDSReading.recorded_at)
            .filter(ERPSUDSReading.session_id == s.id)
            .order_by(desc(ERPSUDSReading.recorded_at))
            .first()
        )
        if last_row:
            end_suds = int(last_row[0])

        mins = int((s.accumulated_seconds or 0) // 60)
        ended = s.ended_at.isoformat() if s.ended_at else "unknown_time"
        return f"Ended {ended}. Duration≈{mins}m. Peak SUDS={peak if peak is not None else 'NA'}, End SUDS={end_suds if end_suds is not None else 'NA'}."