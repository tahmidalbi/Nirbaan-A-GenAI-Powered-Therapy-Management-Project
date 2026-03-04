# app/erp/ERPCoach/nodes/report_generate.py
from __future__ import annotations

from typing import Any, Dict

from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.schemas import TherapistReportJSON, PatientFeedbackJSON

from app.erp.ERPCoach.prompts.report_prompts import (
    build_session_facts_prompt,
    build_therapist_report_prompt,
    build_patient_feedback_prompt,
)


def compress_session_facts(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    Step 1: Turn raw transcript + SUDS + debrief into compact factual bullets (plain text).
    This reduces hallucination risk and makes downstream JSON generation more consistent.

    Produces:
      - session_facts_text (string)
    """
    inputs = state.get("report_inputs") or {}
    prompt = build_session_facts_prompt(
        obsession=inputs["obsession"],
        compulsions=inputs["compulsions"],
        exercise_text=inputs.get("exercise_text"),
        transcript_block=inputs["transcript_block"],
        suds_points_block=inputs["suds_points_block"],
        patient_debrief_text=inputs["patient_debrief_text"],
        prior_summaries=inputs.get("prior_summaries", []),
    )

    # Facts can be plain text; use text_call
    session_facts_text = llm.text_call(prompt=prompt, attempts=3).strip()

    state["session_facts_text"] = session_facts_text
    return state


def generate_therapist_report(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    Step 2: Generate strict JSON TherapistReportJSON from session_facts_text.
    Produces:
      - therapist_report (Pydantic model)
      - therapist_report_json (dict)
    """
    inputs = state.get("report_inputs") or {}
    facts = state.get("session_facts_text", "")

    prompt = build_therapist_report_prompt(
        session_facts=facts,
        elapsed_seconds=float(inputs.get("elapsed_seconds", 0.0)),
        suds_peak=inputs.get("suds_peak"),
        suds_latest=inputs.get("suds_latest"),
    )

    report = llm.structured_call(
        schema=TherapistReportJSON,
        prompt=prompt,
        attempts=3,
        repair_attempts=1,
        repair_context=facts,
    )

    state["therapist_report"] = report
    state["therapist_report_json"] = report.model_dump()
    return state


def generate_patient_feedback(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    Step 3: Generate strict JSON PatientFeedbackJSON from session_facts_text.
    Produces:
      - patient_feedback (Pydantic model)
      - patient_feedback_json (dict)
    """
    inputs = state.get("report_inputs") or {}
    facts = state.get("session_facts_text", "")

    prompt = build_patient_feedback_prompt(
        session_facts=facts,
        elapsed_seconds=float(inputs.get("elapsed_seconds", 0.0)),
        suds_peak=inputs.get("suds_peak"),
        suds_latest=inputs.get("suds_latest"),
    )

    feedback = llm.structured_call(
        schema=PatientFeedbackJSON,
        prompt=prompt,
        attempts=3,
        repair_attempts=1,
        repair_context=facts,
    )

    state["patient_feedback"] = feedback
    state["patient_feedback_json"] = feedback.model_dump()
    return state