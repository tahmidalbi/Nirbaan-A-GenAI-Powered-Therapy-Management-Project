from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.patients.models import Patient
from app.NirbaanAIPatient.models import PsychoeducationChatMessage
from app.erp.models import ERPItem
from app.progress.models import WeeklyProgress


def load_context_node(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Load patient profile, recent chat history, ERP obsession/compulsion pairs,
    and latest weekly progress report from DB.
    No LLM call — pure data retrieval.
    """
    patient_id = state["patient_id"]
    thread_id = state.get("thread_id")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    patient_name = patient.name if patient else "Unknown"
    patient_conditions = patient.conditions if patient else ""
    patient_conditions_description = patient.conditions_description if patient else ""
    patient_address = patient.address if patient else ""

    # Recent chat history from the thread (last 10 turns)
    recent_messages = []
    if thread_id:
        msgs = (
            db.query(PsychoeducationChatMessage)
            .filter(PsychoeducationChatMessage.thread_id == thread_id)
            .order_by(
                PsychoeducationChatMessage.created_at.desc(),
                PsychoeducationChatMessage.id.desc(),
            )
            .limit(10)
            .all()
        )
        for m in reversed(msgs):
            recent_messages.append({"role": m.role, "content": m.content})

    # ERP obsession/compulsion pairs
    erp_items = (
        db.query(ERPItem)
        .filter(ERPItem.patient_id == patient_id)
        .order_by(ERPItem.created_at.asc(), ERPItem.id.asc())
        .all()
    )
    obsession_compulsion_pairs = []
    for item in erp_items:
        compulsions = item.compulsions if isinstance(item.compulsions, list) else []
        obsession_compulsion_pairs.append({
            "erp_item_id": item.id,
            "obsession": (item.obsession or "").strip(),
            "compulsions": [str(c).strip() for c in compulsions if c is not None and str(c).strip()],
        })

    # Latest weekly progress report
    latest_progress = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.patient_id == patient_id)
        .order_by(WeeklyProgress.created_at.desc(), WeeklyProgress.id.desc())
        .first()
    )
    weekly_progress = None
    if latest_progress:
        weekly_progress = {
            "id": latest_progress.id,
            "week_number": latest_progress.week_number,
            "week_start_date": latest_progress.week_start_date,
            "detailed_progress": (latest_progress.detailed_progress or "").strip(),
            "homework_reflection": (latest_progress.homework_reflection or "").strip(),
            "suds_snapshot": latest_progress.suds_snapshot if isinstance(latest_progress.suds_snapshot, list) else None,
        }

    return {
        "patient_name": patient_name,
        "patient_conditions": patient_conditions,
        "patient_conditions_description": patient_conditions_description,
        "patient_address": patient_address,
        "recent_chat_history": recent_messages if recent_messages else state.get("recent_chat_history", []),
        "db_obsession_compulsion_pairs": obsession_compulsion_pairs,
        "db_latest_weekly_progress": weekly_progress,
    }
