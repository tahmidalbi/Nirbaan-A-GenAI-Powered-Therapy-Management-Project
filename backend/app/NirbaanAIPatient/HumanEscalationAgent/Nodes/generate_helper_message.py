from __future__ import annotations

import logging
import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.verifier import (
    ESCALATION_LLM_MAX_RETRIES,
    ESCALATION_LLM_TIMEOUT_SECONDS,
)

log = logging.getLogger(__name__)


class HelperMessageOutput(BaseModel):
    message: str


def fixed_alert_message(state: Dict[str, Any]) -> str:
    """Short alert used when the LLM cannot write one, or when the safety check was unavailable."""
    if state.get("verification_unavailable"):
        header = (
            "Automatic safety check unavailable - this is NOT a confirmed crisis. "
            "Please check in with the patient."
        )
    else:
        header = "URGENT: a patient needs human support."
    lines = [
        header,
        f"Patient: {state.get('patient_name') or 'Unknown'}",
        f"Reason: {state.get('verifier_reasoning') or 'Escalation requested.'}",
        f"Latest message: \"{state.get('user_message', '')}\"",
    ]
    if state.get("patient_address"):
        lines.append(f"Address: {state['patient_address']}")
    lines.append("Please reply in chat and mark that you are handling it.")
    return "\n".join(lines)


def generate_helper_message_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM node that generates a concise, informative message for the human helpers
    group. Includes patient context and the reason for escalation so helpers can
    quickly decide to intervene.

    Delivery never depends on the LLM: if the safety check was unavailable, or the
    LLM call fails, a fixed alert is used instead.
    """

    if state.get("verification_unavailable"):
        return {"helper_message": fixed_alert_message(state)}

    patient_name = state.get("patient_name", "Unknown")
    patient_conditions = state.get("patient_conditions", "")
    patient_conditions_description = state.get("patient_conditions_description", "")
    patient_address = state.get("patient_address", "")
    user_message = state.get("user_message", "")
    verifier_reasoning = state.get("verifier_reasoning", "")
    chat_history = state.get("recent_chat_history", [])
    erp_pairs = state.get("db_obsession_compulsion_pairs", [])
    weekly_progress = state.get("db_latest_weekly_progress")

    history_text = ""
    for turn in chat_history[-6:]:
        role_label = "Patient" if turn["role"] == "user" else "AI Assistant"
        history_text += f"  {role_label}: {turn['content']}\n"

    # Summarise ERP pairs concisely
    erp_text = ""
    if erp_pairs:
        lines = []
        for pair in erp_pairs[:5]:  # cap at 5 most relevant
            compulsions = ", ".join(pair["compulsions"][:3]) if pair["compulsions"] else "none recorded"
            lines.append(f"  - Obsession: {pair['obsession']} | Compulsions: {compulsions}")
        erp_text = "\n".join(lines)
    else:
        erp_text = "No ERP items on record."

    # Summarise latest weekly progress
    progress_text = ""
    if weekly_progress:
        progress_text = (
            f"Week {weekly_progress.get('week_number', '?')} "
            f"({weekly_progress.get('week_start_date', '')}):\n"
            f"  Progress: {weekly_progress.get('detailed_progress', '')[:300]}\n"
            f"  Homework reflection: {weekly_progress.get('homework_reflection', '')[:200]}"
        )
    else:
        progress_text = "No weekly progress report on record."

    prompt = f"""You are composing an urgent alert message for a group of human helpers (emergency personnel) 
who assist therapy patients in real-world situations.

A patient needs human support. Write a clear, concise message that asks a helper to reach out to the patient via chat. Include:
1. States the patient's name and their situation
2. Briefly summarizes why help is needed (based on the escalation reasoning)
3. Includes relevant context from the recent conversation
4. Highlights key ERP obsessions or compulsions that may be active right now
5. Notes recent therapy progress so helpers understand the patient's current stage
6. Notes the patient's address if available
7. Asks one of the helpers to respond in chat and mark that they're handling it

Keep the message professional, compassionate, and actionable. Do not include any PHI beyond 
what's needed for the helpers to respond effectively (they are authorized care team members).

Patient Name: {patient_name}
Patient Conditions: {patient_conditions}
Condition Details: {patient_conditions_description}
Patient Address: {patient_address}

ERP Obsession/Compulsion Profile:
{erp_text}

Latest Weekly Progress:
{progress_text}

Escalation Reason: {verifier_reasoning}

Patient's latest message: "{user_message}"

Recent conversation excerpt:
{history_text}

Write the helper alert message."""

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-2026-03-05"),
            timeout=ESCALATION_LLM_TIMEOUT_SECONDS,
            max_retries=ESCALATION_LLM_MAX_RETRIES,
        ).with_structured_output(HelperMessageOutput)
        message = (llm.invoke(prompt).message or "").strip()
    except Exception as exc:
        log.warning("Helper alert generation failed (%s); using fixed alert", type(exc).__name__)
        message = ""

    return {
        "helper_message": message or fixed_alert_message(state),
    }
