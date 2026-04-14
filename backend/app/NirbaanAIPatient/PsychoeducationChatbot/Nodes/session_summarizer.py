from __future__ import annotations

import os
from typing import Any, Dict

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


class SessionSummaryOutput(BaseModel):
    session_context_summary: str = Field(
        default="",
        description=(
            "A concise 150-200 word summary of the therapy session content that is "
            "relevant to the patient's current message. Empty string if not relevant."
        ),
    )


def session_summarizer_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Summarize the last therapy session transcript focused on what is
    relevant to the patient's current message.

    Inputs expected in state:
    - user_message
    - db_last_therapy_session

    Outputs:
    - session_context_summary
    """
    user_message = (state.get("user_message") or "").strip()
    db_last_therapy_session = state.get("db_last_therapy_session")

    if not user_message or not db_last_therapy_session:
        return {"session_context_summary": ""}

    transcript = (db_last_therapy_session.get("transcript") or "").strip()
    if not transcript:
        return {"session_context_summary": ""}

    session_label = (
        f"Session {db_last_therapy_session.get('session_number', '?')}"
        f" — {db_last_therapy_session.get('title', '')}"
        f" ({db_last_therapy_session.get('session_date', '')})"
    ).strip()

    llm = _get_llm()
    structured_llm = llm.with_structured_output(SessionSummaryOutput)

    prompt = _build_prompt(
        user_message=user_message,
        session_label=session_label,
        transcript=transcript,
    )

    result: SessionSummaryOutput = structured_llm.invoke(prompt)

    return {
        "session_context_summary": (result.session_context_summary or "").strip(),
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.3-chat-latest"),
    )


def _build_prompt(
    *,
    user_message: str,
    session_label: str,
    transcript: str,
) -> str:
    return f"""
You are extracting relevant context from a therapy session transcript for an OCD psychoeducation chatbot.

Your task is NOT to answer the patient.
Your task is ONLY to summarize the parts of the therapy session that are relevant to the patient's current message.

Rules:
1. Focus only on what the therapist discussed that relates to the patient's current message or concern.
2. Keep the summary concise — 150 to 200 words maximum.
3. Do not include unrelated parts of the session.
4. Do not invent or add anything not present in the transcript.
5. If the transcript contains nothing relevant to the patient's current message, return an empty string.
6. Write in third-person summary style (e.g., "The therapist discussed...", "The patient and therapist worked on...").

Patient's current message:
{user_message}

Therapy session: {session_label}

Full session transcript:
{transcript}

Return structured output with:
- session_context_summary
""".strip()
