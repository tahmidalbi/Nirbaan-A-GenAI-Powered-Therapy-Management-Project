from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.erp.models import ERPItem
from app.progress.models import WeeklyProgress
from app.therapy_sessions.models import TherapySession


def db_picker_node(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Load raw DB context candidates for the general support graph.

    This node fetches:
    - all ERP obsession/compulsion pairs for the patient
    - the latest weekly progress report for the patient

    It does NOT decide relevance — downstream nodes use this data directly.
    """
    patient_id = state["patient_id"]

    obsession_compulsion_pairs = _load_erp_pairs(db=db, patient_id=patient_id)
    latest_weekly_progress = _load_latest_weekly_progress(db=db, patient_id=patient_id)
    last_therapy_session = _load_last_therapy_session(db=db, patient_id=patient_id)

    return {
        "db_obsession_compulsion_pairs": obsession_compulsion_pairs,
        "db_latest_weekly_progress": latest_weekly_progress,
        "db_last_therapy_session": last_therapy_session,
    }


def _load_erp_pairs(db: Session, patient_id: int) -> List[Dict[str, Any]]:
    """
    Load all ERP items for the patient as structured obsession-compulsion pairs.
    """
    erp_items = (
        db.query(ERPItem)
        .filter(ERPItem.patient_id == patient_id)
        .order_by(ERPItem.created_at.asc(), ERPItem.id.asc())
        .all()
    )

    results: List[Dict[str, Any]] = []

    for item in erp_items:
        compulsions = item.compulsions if isinstance(item.compulsions, list) else []

        cleaned_compulsions = [
            str(comp).strip()
            for comp in compulsions
            if comp is not None and str(comp).strip()
        ]

        results.append(
            {
                "erp_item_id": item.id,
                "obsession": (item.obsession or "").strip(),
                "compulsions": cleaned_compulsions,
            }
        )

    return results


def _load_latest_weekly_progress(
    db: Session,
    patient_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Load the most recent weekly progress entry for the patient.
    """
    latest = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.patient_id == patient_id)
        .order_by(WeeklyProgress.created_at.desc(), WeeklyProgress.id.desc())
        .first()
    )

    if not latest:
        return None

    suds_snapshot = latest.suds_snapshot if isinstance(latest.suds_snapshot, list) else None

    return {
        "id": latest.id,
        "week_number": latest.week_number,
        "week_start_date": latest.week_start_date,
        "detailed_progress": (latest.detailed_progress or "").strip(),
        "homework_reflection": (latest.homework_reflection or "").strip(),
        "suds_snapshot": suds_snapshot,
    }


def _load_last_therapy_session(
    db: Session,
    patient_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Load the most recent therapy session transcript for the patient.
    therapist_notes are excluded (private).
    """
    session = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == patient_id)
        .order_by(TherapySession.session_date.desc(), TherapySession.id.desc())
        .first()
    )

    if not session:
        return None

    return {
        "session_number": session.session_number,
        "title": (session.title or "").strip(),
        "session_date": session.session_date,
        "transcript": (session.transcript or "").strip(),
    }