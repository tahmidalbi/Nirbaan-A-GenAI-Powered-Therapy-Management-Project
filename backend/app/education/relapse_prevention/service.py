# app/education/relapse_prevention/service.py
from __future__ import annotations
from app.education.relapse_prevention.graph import build_graph

_graph = build_graph()


def generate_education(
    therapist_id: int,
    topic: str = "Relapse prevention for OCD treated with ERP therapy",
) -> dict:
    final_state = _graph.invoke({
        "therapist_id": therapist_id,
        "topic": topic,
    })
    return final_state.get("output_json", {})
