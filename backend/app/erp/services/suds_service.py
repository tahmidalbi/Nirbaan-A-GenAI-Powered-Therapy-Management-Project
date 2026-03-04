# app/erp/services/suds_service.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.erp.models import ERPLiveSession, ERPSUDSReading


class SUDSService:
    """
    Handles:
      - saving SUDS readings during a session
      - updating ERPLiveSession.last_suds_at
      - reading recent SUDS series + peak

    Spike/reminder detection itself should live in the LangGraph compute_metrics node,
    but this service provides the data needed to compute those metrics.
    """

    def __init__(self, db: Session):
        self.db = db

    def submit_suds(
        self,
        *,
        session_id: int,
        patient_id: int,
        suds_value: int,
        elapsed_seconds: float,
    ) -> ERPSUDSReading:
        """
        Saves a SUDS reading for a session.

        - Validates session belongs to patient.
        - Stores elapsed_seconds provided by the client timer.
        - Updates session.last_suds_at for check-in logic.
        """
        if suds_value < 0 or suds_value > 100:
            raise ValueError("suds_value must be between 0 and 100")
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be >= 0")

        session = self._require_session(session_id, patient_id)

        reading = ERPSUDSReading(
            session_id=session.id,
            erp_item_id=session.erp_item_id,
            patient_id=patient_id,
            suds_value=int(suds_value),
            elapsed_seconds=float(elapsed_seconds),
            recorded_at=datetime.utcnow(),
        )
        self.db.add(reading)

        # Update last_suds_at on session (used by reminder logic)
        session.last_suds_at = reading.recorded_at

        self.db.commit()
        self.db.refresh(reading)
        return reading

    def get_recent_suds(
        self,
        *,
        session_id: int,
        patient_id: int,
        limit: int = 12,
    ) -> List[ERPSUDSReading]:
        """
        Returns recent SUDS readings in chronological order (oldest -> newest).
        """
        self._require_session(session_id, patient_id)

        rows = (
            self.db.query(ERPSUDSReading)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.recorded_at))
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    def get_peak_suds(self, *, session_id: int, patient_id: int) -> Optional[int]:
        """
        Returns the maximum suds_value for the session, or None if no readings.
        """
        self._require_session(session_id, patient_id)

        row = (
            self.db.query(ERPSUDSReading.suds_value)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.suds_value))
            .first()
        )
        return int(row[0]) if row else None

    def get_latest_suds(self, *, session_id: int, patient_id: int) -> Optional[Tuple[int, datetime, float]]:
        """
        Returns (suds_value, recorded_at, elapsed_seconds) for the latest reading, or None.
        """
        self._require_session(session_id, patient_id)

        row = (
            self.db.query(ERPSUDSReading.suds_value, ERPSUDSReading.recorded_at, ERPSUDSReading.elapsed_seconds)
            .filter(ERPSUDSReading.session_id == session_id)
            .order_by(desc(ERPSUDSReading.recorded_at))
            .first()
        )
        if not row:
            return None
        return int(row[0]), row[1], float(row[2])

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _require_session(self, session_id: int, patient_id: int) -> ERPLiveSession:
        session = (
            self.db.query(ERPLiveSession)
            .filter(ERPLiveSession.id == session_id, ERPLiveSession.patient_id == patient_id)
            .first()
        )
        if not session:
            raise ValueError(f"ERPLiveSession not found for patient: session_id={session_id}, patient_id={patient_id}")
        return session