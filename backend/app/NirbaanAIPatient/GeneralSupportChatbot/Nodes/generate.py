from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState


class GenerateOutput(BaseModel):
    final_response: str = Field(..., description="Final support message to patient.")


def generate_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Generate the final grounded support response.
    """

    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []

    db_pairs = state.get("db_obsession_compulsion_pairs") or []
    db_latest_progress = state.get("db_latest_weekly_progress")
    db_last_therapy_session = state.get("db_last_therapy_session")
    kb_context_summary = (state.get("kb_context_summary") or "").strip()

    used_sources = _collect_sources(state.get("kb_chunks") or [])

    llm = _get_llm()
    structured_llm = llm.with_structured_output(GenerateOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
        db_last_therapy_session=db_last_therapy_session,
        kb_context_summary=kb_context_summary,
    )

    result: GenerateOutput = structured_llm.invoke(prompt)

    final_response = (result.final_response or "").strip()
    if not final_response:
        final_response = "I’m sorry you’re having a hard time. Try taking one small next step without getting pulled into rituals or overthinking."

    return {
        "final_response": final_response,
        "used_sources": used_sources,
        "final_grounding_summary": kb_context_summary,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2"),
        temperature=0.4,
    )


def _collect_sources(kb_chunks: List[Dict[str, Any]]) -> List[str]:
    # dict.fromkeys maintains insertion order while ensuring uniqueness efficiently
    return list(dict.fromkeys(c.get("source") for c in kb_chunks if c.get("source")))


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    db_pairs: List[Dict[str, Any]],
    db_latest_progress: Dict[str, Any] | None,
    db_last_therapy_session: Dict[str, Any] | None,
    kb_context_summary: str,
) -> str:
    recent_history_text = _format_chat_history(recent_chat_history)
    patient_context_text = _format_patient_context(
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
        db_last_therapy_session=db_last_therapy_session,
    )

    return f"""
You are a supportive OCD therapy assistant helping a patient between therapy sessions.

Your role is to provide therapist KB grounded support consistent with OCD treatment principles.

Patient is already doing therapy under a therapist, so do not suggest to see a therapist or a crisis line. Just provide support consistent with what a therapist-assistant might say to help them cope in the moment, based on the therapist KB.

CRITICAL RULES:

1. You must use the therapist KB guidance as the foundation for your response.
2. DO NOT provide reassurance about feared outcomes.
3. DO NOT guarantee safety or certainty.
4. DO NOT help the patient neutralize intrusive thoughts.
5. Encourage tolerance of uncertainty.
6. Encourage response prevention rather than rituals.
7. Validate emotional difficulty without validating OCD fears.
8. No need to ask patient if they are feeling any self-harm urge, just provide support consistent with OCD treatment principles all grounded on therapist KB.
9. Do not ask to do something for a certain time, like don't respond with timer based instructions.

Patient message:
{user_message}

Recent conversation:
{recent_history_text}

Patient context:
{patient_context_text}

Therapist KB grounding:
{kb_context_summary or "No therapist KB grounding available."}

Instructions:

- Provide compassionate, calm support.
- Help the patient tolerate uncertainty rather than eliminate it.
- Encourage ERP-consistent responses when relevant.
- Avoid sounding clinical or robotic.
- Speak naturally like a supportive coach.
- Keep the response supportive, grounded, and not overly long.

Write the final response to the patient.
""".strip()


def _format_chat_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No recent history."

    lines: List[str] = []

    for msg in history[-6:]:
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "").strip()

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def _format_patient_context(
    *,
    db_pairs: List[Dict[str, Any]],
    db_latest_progress: Dict[str, Any] | None,
    db_last_therapy_session: Dict[str, Any] | None,
) -> str:
    parts: List[str] = []

    if db_pairs:
        pair_lines: List[str] = []
        for pair in db_pairs:
            obs = (pair.get("obsession") or "").strip()
            comps = pair.get("compulsions") or []
            comp_text = ", ".join(str(c).strip() for c in comps if c and str(c).strip())
            line = f"- Obsession: {obs or 'N/A'}"
            if comp_text:
                line += f" | Compulsions: {comp_text}"
            pair_lines.append(line)
        parts.append("Obsession-compulsion pairs:\n" + "\n".join(pair_lines))

    if db_latest_progress:
        week = db_latest_progress.get("week_number")
        detail = (db_latest_progress.get("detailed_progress") or "").strip()
        if detail:
            parts.append(f"Latest weekly progress (week {week}):\n{detail}")

    if db_last_therapy_session:
        session_text = (
            f"Session {db_last_therapy_session.get('session_number', '?')}"
            f" — {db_last_therapy_session.get('title', '')}"
            f" ({db_last_therapy_session.get('session_date', '')})"
            f"\n{db_last_therapy_session.get('transcript', '')}"
        ).strip()
        parts.append(f"Last therapy session:\n{session_text}")

    return "\n\n".join(parts).strip() if parts else "No patient context available."