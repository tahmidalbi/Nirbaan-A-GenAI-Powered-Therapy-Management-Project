from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAITherapist.state import NirbaanAITherapistState


class ClarificationCheckOutput(BaseModel):
    needs_clarification: bool = Field(
        ...,
        description="Whether the AI needs a clarification answer from the therapist before finalizing the analysis."
    )
    clarification_question: str = Field(
        default="",
        description="A concise question for the therapist if clarification is needed."
    )


def clarification_checker_node(state: NirbaanAITherapistState) -> Dict[str, Any]:
    """
    Decide whether the therapist-side analysis needs a clarification checkpoint.
    """

    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    analysis_goal = (state.get("analysis_goal") or "").strip()

    patient_context_summary = (state.get("patient_context_summary") or "").strip()
    kb_context_summary = (state.get("kb_context_summary") or "").strip()

    draft_analysis = (state.get("draft_analysis") or "").strip()
    analysis_summary = (state.get("analysis_summary") or "").strip()

    llm = _get_llm()
    structured_llm = llm.with_structured_output(ClarificationCheckOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        analysis_goal=analysis_goal,
        patient_context_summary=patient_context_summary,
        kb_context_summary=kb_context_summary,
        draft_analysis=draft_analysis,
        analysis_summary=analysis_summary,
    )

    result: ClarificationCheckOutput = structured_llm.invoke(prompt)

    needs_clarification = bool(result.needs_clarification)
    clarification_question = (result.clarification_question or "").strip()

    if not needs_clarification:
        clarification_question = ""

    return {
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2"),
        temperature=0,
    )


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    analysis_goal: str,
    patient_context_summary: str,
    kb_context_summary: str,
    draft_analysis: str,
    analysis_summary: str,
) -> str:
    recent_history_text = _format_chat_history(recent_chat_history)

    return f"""
You are checking whether an OCD patient-analysis workflow needs a human-in-the-loop clarification from the therapist.

Your task is NOT to continue the analysis.
Your task is ONLY to decide whether the AI should pause and ask the therapist one clarification question.

When clarification is needed:
- A key ambiguity would materially change the analysis.
- A missing therapist judgment/case formulation detail is important.
- The AI would otherwise risk overinterpreting the patient.

When clarification is NOT needed:
- The current patient context + therapist KB are sufficient.
- The uncertainty is minor and does not block useful analysis.
- The analysis can be finalized responsibly without asking.

Rules:
1. Ask for clarification only if it would meaningfully improve the analysis.
2. Do not ask trivial or overly broad questions.
3. If clarification is needed, ask exactly one concise, high-value question.
4. Do not invent patient facts.
5. If no clarification is needed, set clarification_question to an empty string.

Therapist current message:
{user_message}

Recent therapist chat context:
{recent_history_text}

Analysis goal:
{analysis_goal or "No explicit analysis goal provided."}

Patient context summary:
{patient_context_summary or "No patient context summary available."}

Therapist KB grounding:
{kb_context_summary or "No therapist KB grounding available."}

Current draft analysis:
{draft_analysis or "No draft analysis available."}

Current analysis summary:
{analysis_summary or "No analysis summary available."}

Return structured output with:
- needs_clarification
- clarification_question
""".strip()


def _format_chat_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No recent therapist chat history."

    lines: List[str] = []

    for msg in history[-6:]:
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "").strip()

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


