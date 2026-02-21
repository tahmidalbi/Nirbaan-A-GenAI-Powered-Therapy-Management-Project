# app/ai_ladder_review/data_loader.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.intakes.models import PatientIntake
from app.self_monitoring.models import SelfMonitoringDay, SelfMonitoringEntry
from app.fear_ladder.models import FearLadderItem


@dataclass
class LadderReviewData:
    intake: Optional[PatientIntake]
    log_entries: List[SelfMonitoringEntry]
    ladder_items: List[FearLadderItem]


def load_intake(db: Session, patient_id: int) -> Optional[PatientIntake]:
    return (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient_id)
        .first()
    )


def load_last_7_days_logs(db: Session, patient_id: int) -> List[SelfMonitoringEntry]:
    """
    SelfMonitoringEntry.date is stored as ISO string YYYY-MM-DD.
    We filter inclusively for [today-6, today] (7 days total).
    """
    today: date = datetime.utcnow().date()
    start: date = today - timedelta(days=6)

    start_s = start.isoformat()
    end_s = today.isoformat()

    # Join to enforce patient ownership via SelfMonitoringDay
    q = (
        db.query(SelfMonitoringEntry)
        .join(SelfMonitoringDay, SelfMonitoringEntry.day_id == SelfMonitoringDay.id)
        .filter(SelfMonitoringDay.patient_id == patient_id)
        .filter(SelfMonitoringEntry.date >= start_s)
        .filter(SelfMonitoringEntry.date <= end_s)
        .order_by(SelfMonitoringEntry.date.asc(), SelfMonitoringEntry.time.asc())
    )
    return q.all()


def load_ladder_items(db: Session, ladder_id: int) -> List[FearLadderItem]:
    return (
        db.query(FearLadderItem)
        .filter(FearLadderItem.fear_ladder_id == ladder_id)
        .order_by(FearLadderItem.order_index.asc())
        .all()
    )


def normalize_payload(intake: Optional[PatientIntake], log_entries: List[SelfMonitoringEntry]) -> Dict[str, Any]:
    """
    Produces:
    {
      "intake": [{"source_id": "...", "field": "...", "text": "..."}],
      "logs": [{"source_id": "...", "date": "...", "time": "...", "event": "...", "ritual": "...", ...}]
    }
    """
    intake_blocks: List[Dict[str, Any]] = []
    if intake is not None:
        sid = str(intake.id)

        def add(field: str, text: Optional[str]) -> None:
            if text is None:
                return
            t = str(text).strip()
            if not t:
                return
            intake_blocks.append({"source_id": sid, "field": field, "text": t})

        add("your_story", intake.your_story)
        add("when_started", intake.when_started)
        add("affected_life_areas", intake.affected_life_areas)
        add("other_conditions", intake.other_conditions)

        # issues is a list[dict] like [{"issue": "...", "severity": 8}, ...]
        if intake.issues:
            parts = []
            for it in intake.issues:
                issue = str(it.get("issue", "")).strip()
                sev = it.get("severity", None)
                if issue:
                    if sev is None:
                        parts.append(issue)
                    else:
                        parts.append(f"{issue} ({sev}/10)")
            if parts:
                intake_blocks.append({"source_id": sid, "field": "issues", "text": "; ".join(parts)})

    logs_blocks: List[Dict[str, Any]] = []
    for e in log_entries or []:
        logs_blocks.append(
            {
                "source_id": str(e.id),
                "date": e.date,
                "time": e.time,
                "event": e.event,
                "ritual": e.ritual,
                "anxiety_level": e.anxiety_level,
                "time_spent_min": float(e.time_spent),
            }
        )

    return {"intake": intake_blocks, "logs": logs_blocks}


def ladder_text(items: List[FearLadderItem]) -> str:
    lines: List[str] = []
    for it in items or []:
        suds = it.suds
        text = (it.item or "").strip()
        if not text:
            continue
        lines.append(f"[SUDS {suds}] {text}")
    return "\n".join(lines)