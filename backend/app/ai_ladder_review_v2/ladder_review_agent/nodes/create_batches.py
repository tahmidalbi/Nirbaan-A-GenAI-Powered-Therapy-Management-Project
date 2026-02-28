# ai_ladder_review_v2/ladder_review_agent/nodes/create_batches.py
from __future__ import annotations

from typing import Any, Dict, List

from ..state import LadderReviewState


def _safe(x: Any) -> str:
    return "" if x is None else str(x).strip()


def _entry_to_line(e: Dict[str, Any]) -> str:
    """
    IMPORTANT: We include [E<entry_id>] so the LLM can quote evidence that maps back.
    """
    entry_id = _safe(e.get("entry_id"))
    date = _safe(e.get("date"))
    time = _safe(e.get("time"))
    event = _safe(e.get("event"))
    ritual = _safe(e.get("ritual"))
    spent = _safe(e.get("time_spent"))
    anx = _safe(e.get("anxiety_level"))

    return (
        f"[E{entry_id}] DATE:{date} TIME:{time} | "
        f"EVENT:{event} | RITUAL:{ritual} | "
        f"TIME_SPENT_MIN:{spent} | ANXIETY:{anx}/10"
    ).strip()


def create_batches_node(
    state: LadderReviewState,
    *,
    max_entries_per_batch: int = 40,
) -> LadderReviewState:
    """
    NO LLM.
    Splits self-monitoring entries into batches by entry count.
    """
    entries = state.logs_raw or []
    if not entries:
        state.batches = []
        state.batch_index = 0
        state.batch_retry_count = 0
        state.log_trace("create_batches", {"batches": 0, "total_entries": 0})
        return state

    lines = [_entry_to_line(e) for e in entries]
    batches: List[Dict[str, Any]] = []

    batch_id = 1
    for i in range(0, len(lines), max_entries_per_batch):
        chunk = lines[i : i + max_entries_per_batch]
        chunk_entries = entries[i : i + max_entries_per_batch]

        text = "\n".join(f"- {ln}" for ln in chunk)

        batches.append(
            {
                "batch_id": f"B{batch_id}",
                "text": text,
                "meta": {
                    "entry_count": len(chunk),
                    "entry_ids": [ce.get("entry_id") for ce in chunk_entries],
                    "date_from": chunk_entries[0].get("date") if chunk_entries else None,
                    "date_to": chunk_entries[-1].get("date") if chunk_entries else None,
                },
            }
        )
        batch_id += 1

    state.batches = batches
    state.batch_index = 0
    state.batch_retry_count = 0

    state.log_trace(
        "create_batches",
        {"batches": len(batches), "total_entries": len(entries), "max_entries_per_batch": max_entries_per_batch},
    )
    return state