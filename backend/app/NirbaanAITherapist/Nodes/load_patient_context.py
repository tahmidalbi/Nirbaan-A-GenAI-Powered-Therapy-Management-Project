from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.erp.models import ERPItem
from app.fear_ladder.models import FearLadder
from app.progress.models import WeeklyProgress


def load_patient_context_node(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Load therapist-side patient context for analysis.

    Included context:
    - latest weekly progress report
    - initial fear ladder
    - ERP obsession-compulsion pairs
    """

    patient_id = state["patient_id"]

    latest_weekly_progress = _load_latest_weekly_progress(db=db, patient_id=patient_id)
    initial_fear_ladder = _load_initial_fear_ladder(db=db, patient_id=patient_id)
    obsession_compulsion_pairs = _load_erp_pairs(db=db, patient_id=patient_id)

    patient_context_summary = _build_patient_context_summary(
        latest_weekly_progress=latest_weekly_progress,
        initial_fear_ladder=initial_fear_ladder,
        obsession_compulsion_pairs=obsession_compulsion_pairs,
    )

    return {
        "latest_weekly_progress": latest_weekly_progress,
        "initial_fear_ladder": initial_fear_ladder,
        "obsession_compulsion_pairs": obsession_compulsion_pairs,
        "patient_context_summary": patient_context_summary,
    }


def _load_latest_weekly_progress(
    db: Session,
    patient_id: int,
) -> Optional[Dict[str, Any]]:
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


def _load_initial_fear_ladder(
    db: Session,
    patient_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Load the earliest fear ladder for the patient as the 'initial' fear ladder.
    """
    ladder = (
        db.query(FearLadder)
        .options(joinedload(FearLadder.items))
        .filter(FearLadder.patient_id == patient_id)
        .order_by(FearLadder.created_at.asc(), FearLadder.id.asc())
        .first()
    )

    if not ladder:
        return None

    items = sorted(ladder.items or [], key=lambda x: (x.order_index, x.id))

    return {
        "id": ladder.id,
        "status": ladder.status.value if hasattr(ladder.status, "value") else str(ladder.status),
        "created_at": ladder.created_at.isoformat() if ladder.created_at else None,
        "items": [
            {
                "id": item.id,
                "item": (item.item or "").strip(),
                "suds": item.suds,
                "order_index": item.order_index,
            }
            for item in items
        ],
    }


def _load_erp_pairs(
    db: Session,
    patient_id: int,
) -> List[Dict[str, Any]]:
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
                "latest_session_id": item.latest_session_id,
                "suds": item.suds,
            }
        )

    return results


def _build_patient_context_summary(
    *,
    latest_weekly_progress: Optional[Dict[str, Any]],
    initial_fear_ladder: Optional[Dict[str, Any]],
    obsession_compulsion_pairs: List[Dict[str, Any]],
) -> str:
    parts: List[str] = []

    if latest_weekly_progress:
        progress_lines: List[str] = []
        progress_lines.append(
            f"Latest weekly progress: week {latest_weekly_progress.get('week_number')} "
            f"(start date: {latest_weekly_progress.get('week_start_date')})"
        )

        detailed_progress = (latest_weekly_progress.get("detailed_progress") or "").strip()
        homework_reflection = (latest_weekly_progress.get("homework_reflection") or "").strip()
        suds_snapshot = latest_weekly_progress.get("suds_snapshot")

        if detailed_progress:
            progress_lines.append(f"Detailed progress: {detailed_progress}")

        if homework_reflection:
            progress_lines.append(f"Homework reflection: {homework_reflection}")

        if suds_snapshot:
            progress_lines.append(f"SUDS snapshot: {suds_snapshot}")

        parts.append("\n".join(progress_lines))

    if initial_fear_ladder:
        ladder_lines: List[str] = []
        ladder_lines.append(
            f"Initial fear ladder (status: {initial_fear_ladder.get('status')}):"
        )

        ladder_items = initial_fear_ladder.get("items") or []
        if ladder_items:
            for item in ladder_items[:12]:
                ladder_lines.append(
                    f"- {item.get('item')} (SUDS: {item.get('suds')}, order: {item.get('order_index')})"
                )
        else:
            ladder_lines.append("- No items found.")

        parts.append("\n".join(ladder_lines))

    if obsession_compulsion_pairs:
        erp_lines: List[str] = []
        erp_lines.append("ERP obsession-compulsion pairs:")

        for pair in obsession_compulsion_pairs[:15]:
            obsession = pair.get("obsession") or "N/A"
            compulsions = pair.get("compulsions") or []
            comp_text = ", ".join(compulsions) if compulsions else "none listed"

            erp_lines.append(
                f"- Obsession: {obsession} | Compulsions: {comp_text}"
            )

        parts.append("\n".join(erp_lines))

    return "\n\n".join(parts).strip()