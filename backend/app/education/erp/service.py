# app/education/erp/service.py
from __future__ import annotations
from app.education.erp.graph import build_graph

_graph = build_graph()


def generate_education(
    therapist_id: int,
    topic: str = "Exposure and Response Prevention (ERP) for OCD — how it works, what to expect, and how to build your practice",
) -> dict:
    final_state = _graph.invoke({
        "therapist_id": therapist_id,
        "topic": topic,
    })
    return final_state.get("output_json", {})
