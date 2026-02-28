# ai_ladder_review_v2/ladder_review_agent/state.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LadderReviewState:
    """
    LangGraph state for the Hidden Symptom Detector (Ladder Review Agent).

    This state is intentionally explicit and simple:
    - Nodes read from and write to this object.
    - batch_index + batch_retry_count control the batch loop + bounded rechecks.
    """

    # --- identity / orchestration ---
    review_id: str = ""
    patient_id: str = ""
    therapist_id: str = ""

    # --- loaded context (Node: load_context) ---
    intake_text: str = ""                 # raw or summarized intake text
    ladder_raw_text: str = ""             # patient ladder text (raw)
    logs_raw: List[Dict[str, Any]] = field(default_factory=list)  # raw logs list (dicts)

    # --- ladder extraction (Node: ladder_extractor) ---
    ladder_items: List[Dict[str, Any]] = field(default_factory=list)  # normalized ladder items
    ladder_text: str = ""                 # optional compact text summary of ladder (for matching)

    # --- batching (Node: create_batches) ---
    batches: List[Dict[str, Any]] = field(default_factory=list)
    # Each batch dict should include at least:
    # {
    #   "batch_id": "B1",
    #   "text": "...",
    #   "meta": {"date_from": "...", "date_to": "...", "entry_count": 12}
    # }

    batch_index: int = 0
    batch_retry_count: int = 0
    max_batch_retries: int = 2

    # --- per-batch working set (Nodes: taxonomy_retriever_node / symptom_finder / checker) ---
    taxonomy_context_text: str = ""       # joined retrieved chunk texts for current batch
    retrieved_taxonomy_titles: List[str] = field(default_factory=list)  # debug/UI: which chunks were injected

    batch_candidates: List[Dict[str, Any]] = field(default_factory=list)  # output of symptom finder for current batch
    recheck: bool = False
    recheck_reason: str = ""
    recheck_query: str = ""               # LLM-suggested keywords to bias retrieval on recheck

    # --- merged candidates across all batches ---
    candidates_all: List[Dict[str, Any]] = field(default_factory=list)

    # --- hidden matcher (Node: hidden_matcher) ---
    missing_ids: List[str] = field(default_factory=list)

    # --- final output / persistence ---
    result_payload: Dict[str, Any] = field(default_factory=dict)

    # --- errors / tracing ---
    errors: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def current_batch(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.batch_index < len(self.batches):
            return self.batches[self.batch_index]
        return None

    def is_done(self) -> bool:
        return self.batch_index >= len(self.batches)

    def log_trace(self, node: str, info: Dict[str, Any]) -> None:
        """Store lightweight debug traces to help you see what happened in production."""
        self.trace.append({"node": node, **info})