# ai_ladder_review_v2/ladder_review_agent/nodes/load_context.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..state import LadderReviewState

from app.fear_ladder.models import AILadderReview, FearLadder, FearLadderItem
from app.intakes.models import PatientIntake
from app.self_monitoring.models import SelfMonitoringDay, SelfMonitoringEntry


def _require(value: Any, msg: str) -> Any:
    if value is None:
        raise RuntimeError(msg)
    return value


def _ladder_items_to_raw_text(items: List[FearLadderItem]) -> str:
    # patient-created ladder item text is in FearLadderItem.item
    lines: List[str] = []
    for it in sorted(items, key=lambda x: x.order_index):
        lines.append(f"- ({it.suds}/100) {it.item}")
    return "\n".join(lines).strip()


def _intake_to_text(intake: PatientIntake) -> str:
    # Keep it simple: join key fields + issues list
    issues = intake.issues or []
    issues_txt = "\n".join([f"- {i.get('issue','')}: {i.get('severity','')}" for i in issues]) if issues else ""

    parts = [
        f"YOUR_STORY:\n{intake.your_story}",
        f"WHEN_STARTED:\n{intake.when_started}",
        f"PREVIOUS_THERAPY:\n{intake.previous_therapy_details or ''}",
        f"MEDICATION:\n{intake.medication_details or ''}",
        f"AFFECTED_LIFE_AREAS:\n{intake.affected_life_areas or ''}",
        f"OTHER_CONDITIONS:\n{intake.other_conditions or ''}",
        f"ISSUES (severity):\n{issues_txt}".strip(),
    ]
    return "\n\n".join([p for p in parts if p.strip()]).strip()


def load_context_node(
    db: Session,
    state: LadderReviewState,
    *,
    days_back: int = 14,
) -> LadderReviewState:
    """
    Load context for this review_id (NO LLM):
      - review row (patient_id, therapist_id, ladder_id)
      - ladder raw text (from FearLadderItem.item)
      - intake text (PatientIntake)
      - self monitoring entries for last N days
    """
    if not state.review_id:
        raise RuntimeError("state.review_id is required")

    review: Optional[AILadderReview] = db.get(AILadderReview, int(state.review_id))
    review = _require(review, f"AILadderReview not found for id={state.review_id}")

    state.patient_id = str(review.patient_id)
    state.therapist_id = str(review.therapist_id)

    ladder: Optional[FearLadder] = db.get(FearLadder, int(review.ladder_id))
    ladder = _require(ladder, f"FearLadder not found for id={review.ladder_id}")

    ladder_items = db.execute(
        select(FearLadderItem).where(FearLadderItem.fear_ladder_id == ladder.id)
    ).scalars().all()

    state.ladder_raw_text = _ladder_items_to_raw_text(ladder_items)

    intake = db.execute(
        select(PatientIntake)
        .where(PatientIntake.patient_id == review.patient_id)
        .order_by(PatientIntake.created_at.desc())
        .limit(1)
    ).scalars().first()
    intake = _require(intake, f"PatientIntake not found for patient_id={review.patient_id}")

    state.intake_text = _intake_to_text(intake)

    # Load recent self monitoring entries
    # We’ll fetch days first, then entries via relationship to keep it simple.
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    days = db.execute(
        select(SelfMonitoringDay)
        .where(SelfMonitoringDay.patient_id == review.patient_id)
        .where(SelfMonitoringDay.created_at >= cutoff)
        .options(selectinload(SelfMonitoringDay.entries))
        .order_by(SelfMonitoringDay.created_at.asc())
    ).scalars().all()

    logs_raw: List[Dict[str, Any]] = []
    for d in days:
        for e in (d.entries or []):
            logs_raw.append(
                {
                    "day_id": d.id,
                    "entry_id": e.id,
                    "date": e.date,
                    "time": e.time,
                    "event": e.event,
                    "ritual": e.ritual,
                    "time_spent": e.time_spent,
                    "anxiety_level": e.anxiety_level,
                }
            )

    # sort by date+time if present
    logs_raw.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    state.logs_raw = logs_raw

    state.log_trace(
        "load_context",
        {
            "review_id": state.review_id,
            "patient_id": state.patient_id,
            "ladder_items_count": len(ladder_items),
            "logs_entries_count": len(state.logs_raw),
            "days_loaded": len(days),
        },
    )
    return state