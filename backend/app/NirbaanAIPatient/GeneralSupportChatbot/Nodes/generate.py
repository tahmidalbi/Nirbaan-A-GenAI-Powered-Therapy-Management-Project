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
    session_context_summary = (state.get("session_context_summary") or "").strip()

    used_sources = _collect_sources(state.get("kb_chunks") or [])

    llm = _get_llm()
    structured_llm = llm.with_structured_output(GenerateOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
        session_context_summary=session_context_summary,
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
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.3-chat-latest"),
        
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
    session_context_summary: str,
    kb_context_summary: str,
) -> str:
    recent_history_text = _format_chat_history(recent_chat_history)
    patient_context_text = _format_patient_context(
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
    )

    return f"""
You are a supportive OCD therapy assistant helping a patient between therapy sessions.

Your role is to provide grounded, warm support consistent with OCD/ERP treatment principles, based on the therapist's knowledge base.

The patient is already in therapy. Do not suggest they see a therapist or call a crisis line. Respond as a knowledgeable, caring coach who knows their situation.

CRITICAL RULES:

1. Ground your response in the therapist KB guidance provided below. That is your primary source.
2. If no therapist KB grounding is available, keep the response brief, empathetic, and based only on general OCD/ERP principles — do not fabricate clinical guidance.
3. DO NOT provide reassurance about feared outcomes.
4. DO NOT guarantee safety or certainty.
5. DO NOT help the patient neutralize intrusive thoughts.
6. Encourage tolerance of uncertainty.
7. Encourage response prevention rather than rituals.
8. Validate the emotional difficulty without validating the OCD fear itself.
9. Do not ask about self-harm. Just provide OCD-consistent support grounded on the therapist KB.
10. Do not give timer-based instructions (e.g., "do this for 10 minutes").
11. HARM OCD RULE: If the patient has harm-themed obsessions or intrusive thoughts, treat these as ego-dystonic OCD — NOT genuine intent or risk. Do NOT suggest crisis lines or ask if they want to hurt themselves or others. Respond with OCD-consistent support.
12. PERSONALIZATION: Patient-specific context is provided below (their obsessions, compulsions, progress, last session themes). Use it naturally when it is clearly relevant to their current message — for example, if their message relates directly to one of their listed obsessions or something covered in the last session, reference it by name rather than speaking generically. Do not force personalization when the message is general.

Patient message:
{user_message}

Recent conversation:
{recent_history_text}

Patient context (obsessions, compulsions, recent progress — use to personalize when relevant):
{patient_context_text}

Last therapy session context (relevant excerpt summary — use to connect response to recent session themes):
{session_context_summary or "Not available."}

Therapist KB grounding (your primary foundation — prioritize this):
{kb_context_summary or "No therapist KB grounding available."}

Response style:
- Compassionate, calm, and natural — like a supportive coach, not a clinical manual.
- Speak directly to the patient in second person.
- Keep it focused and not overly long.

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

    return "\n\n".join(parts).strip() if parts else "No patient context available."