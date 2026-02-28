# app/education/fear_ladder/service.py
from __future__ import annotations
from sqlalchemy.orm import Session
from app.education.fear_ladder.graph import build_graph
from app.database.session import SessionLocal

_graph = build_graph(SessionLocal)

def generate_education(therapist_id: int, topic: str = "Fear ladder (exposure hierarchy) in ERP for OCD") -> dict:
    final_state = _graph.invoke({
        "therapist_id": therapist_id,
        "topic": topic,
    })
    return final_state.get("output_json", {})  # already strict schema