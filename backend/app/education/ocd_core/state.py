# app/education/ocd_core/state.py
from __future__ import annotations
from typing import Any, Dict, List, TypedDict


class KBChunk(TypedDict):
    chunk_text: str
    resource_title: str
    resource_id: int
    similarity_score: float


class OCDEducationState(TypedDict, total=False):
    therapist_id: int
    topic: str

    kb_chunks: List[KBChunk]
    kb_sufficient: bool
    kb_reason: str

    web_results: List[Dict[str, Any]]
    output_json: Dict[str, Any]
