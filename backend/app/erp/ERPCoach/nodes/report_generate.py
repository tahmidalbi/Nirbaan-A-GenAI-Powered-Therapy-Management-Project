# app/erp/ERPCoach/nodes/report_generate.py
from __future__ import annotations

from typing import Any, Dict

from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.schemas import TherapistReportJSON, PatientFeedbackJSON, CrossSessionOverviewResult

from app.erp.ERPCoach.prompts.report_prompts import (
    build_session_facts_prompt,
    build_therapist_report_prompt,
    build_patient_feedback_prompt,
    build_cross_session_overview_prompt,
)
from app.erp.ERPCoach.nodes.report_bundle import format_session_report_block


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
    prior_reports_block = inputs.get("prior_reports_block", "")

    prompt = build_therapist_report_prompt(
        session_facts=facts,
        elapsed_seconds=float(inputs.get("elapsed_seconds", 0.0)),
        suds_peak=inputs.get("suds_peak"),
        suds_latest=inputs.get("suds_latest"),
        prior_reports_block=prior_reports_block,
    )

    report = llm.structured_call(
        schema=TherapistReportJSON,
        prompt=prompt,
        attempts=3,
        repair_attempts=1,
        repair_context=facts,
    )

    # If the LLM left cross_session_overview null despite having prior session data,
    # run a dedicated focused call to populate it. This handles cases where the LLM
    # ignores the instruction buried in the large combined prompt.
    if report.cross_session_overview is None and prior_reports_block.strip():
        current_block = format_session_report_block(report.model_dump())
        cso_prompt = build_cross_session_overview_prompt(
            current_session_block=current_block,
            prior_reports_block=prior_reports_block,
        )
        cso_result = llm.structured_call(
            schema=CrossSessionOverviewResult,
            prompt=cso_prompt,
            attempts=3,
        )
        # Only patch if the dedicated call produced actual content
        cso_dict = cso_result.model_dump()
        if cso_dict.get("summary") or cso_dict.get("common_patterns") or cso_dict.get("blockers_to_progress"):
            report_dict = report.model_dump()
            report_dict["cross_session_overview"] = cso_dict
            report = TherapistReportJSON.model_validate(report_dict)

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