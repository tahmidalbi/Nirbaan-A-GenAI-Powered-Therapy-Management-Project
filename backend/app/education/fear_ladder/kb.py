# app/education/fear_ladder/kb.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session

from app.resources.rag_service import rag_service
from app.education.fear_ladder.state import KBChunk
from app.education.fear_ladder.config import KB_TOP_K

def retrieve_kb(db: Session, therapist_id: int, query: str) -> List[KBChunk]:
    return rag_service.retrieve_chunks(
        db=db,
        therapist_id=therapist_id,
        query=query,
        top_k=KB_TOP_K
    )  # type: ignore[return-value]

def kb_context(chunks: List[KBChunk], max_chars: int = 7000) -> str:
    parts = []
    total = 0
    for i, c in enumerate(chunks, 1):
        block = (
            f"[KB {i}: {c['resource_title']} | sim={c['similarity_score']:.3f} | resource_id={c['resource_id']}]\n"
            f"{c['chunk_text']}\n"
        )
        total += len(block)
        if total > max_chars:
            break
        parts.append(block)
    return "\n---\n".join(parts)