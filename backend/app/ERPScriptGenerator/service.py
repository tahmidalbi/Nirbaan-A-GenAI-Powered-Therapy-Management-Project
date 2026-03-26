from __future__ import annotations

from uuid import uuid4
from langgraph.types import Command

from .schemas import StartImaginalRunRequest, ReviewImaginalRunRequest


def start_run(graph, payload: StartImaginalRunRequest):
    thread_id = f"imaginal-{payload.patient_id}-{payload.erp_item_id}-{payload.therapist_id}-{uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    graph.invoke(
        {
            "thread_id": thread_id,
            "patient_id": payload.patient_id,
            "therapist_id": payload.therapist_id,
            "erp_item_id": payload.erp_item_id,
            "feared_consequence": payload.feared_consequence,
            "script_intensity": payload.script_intensity,
            "subtype": payload.subtype,
        },
        config=config,
    )
    return config


def resume_run(graph, payload: ReviewImaginalRunRequest):
    config = {"configurable": {"thread_id": payload.thread_id}}
    decision = {
        "approved": payload.approved,
        "feedback": payload.feedback,
    }
    graph.invoke(Command(resume=decision), config=config)
    return config