from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAITherapist.state import NirbaanAITherapistState


class ResumeWithClarificationOutput(BaseModel):
    draft_analysis: str = Field(
        ...,
        description="Updated internal fuller patient analysis draft after using the therapist clarification."
    )
    analysis_summary: str = Field(
        ...,
        description="Updated clean therapist-facing analysis summary after using the therapist clarification."
    )


def resume_with_clarification_node(
    state: NirbaanAITherapistState,
) -> Dict[str, Any]:
    """
    Resume therapist-side patient analysis after a clarification answer is provided.
    """

    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    analysis_goal = (state.get("analysis_goal") or "").strip()

    patient_context_summary = (state.get("patient_context_summary") or "").strip()
    kb_context_summary = (state.get("kb_context_summary") or "").strip()

    draft_analysis = (state.get("draft_analysis") or "").strip()
    analysis_summary = (state.get("analysis_summary") or "").strip()

    clarification_question = (state.get("clarification_question") or "").strip()
    clarification_answer = (state.get("clarification_answer") or "").strip()

    latest_weekly_progress = state.get("latest_weekly_progress")
    initial_fear_ladder = state.get("initial_fear_ladder")
    obsession_compulsion_pairs = state.get("obsession_compulsion_pairs") or []
    kb_chunks = state.get("kb_chunks") or []

    if not clarification_answer:
        return {
            "draft_analysis": draft_analysis,
            "analysis_summary": analysis_summary,
            "needs_clarification": True,
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(ResumeWithClarificationOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        analysis_goal=analysis_goal,
        patient_context_summary=patient_context_summary,
        latest_weekly_progress=latest_weekly_progress,
        initial_fear_ladder=initial_fear_ladder,
        obsession_compulsion_pairs=obsession_compulsion_pairs,
        kb_context_summary=kb_context_summary,
        prior_draft_analysis=draft_analysis,
        prior_analysis_summary=analysis_summary,
        clarification_question=clarification_question,
        clarification_answer=clarification_answer,
    )

    result: ResumeWithClarificationOutput = structured_llm.invoke(prompt)

    used_sources = _collect_sources(kb_chunks)

    return {
        "draft_analysis": (result.draft_analysis or "").strip(),
        "analysis_summary": (result.analysis_summary or "").strip(),
        "used_sources": used_sources,
        "needs_clarification": False,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.3-chat-latest"),
        
    )


def _collect_sources(kb_chunks: List[Dict[str, Any]]) -> List[str]:
    sources: List[str] = []

    for chunk in kb_chunks:
        src = chunk.get("source")
        if src and src not in sources:
            sources.append(src)

    return sources

                       
def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    analysis_goal: str,
    patient_context_summary: str,
    latest_weekly_progress: Dict[str, Any] | None,
    initial_fear_ladder: Dict[str, Any] | None,
    obsession_compulsion_pairs: List[Dict[str, Any]],
    kb_context_summary: str,
    prior_draft_analysis: str,
    prior_analysis_summary: str,               
    clarification_question: str,
    clarification_answer: str,
) -> str:
    recent_history_text = _format_chat_history(recent_chat_history)
    weekly_progress_text = _format_weekly_progress(latest_weekly_progress)
    fear_ladder_text = _format_fear_ladder(initial_fear_ladder)
    erp_pairs_text = _format_erp_pairs(obsession_compulsion_pairs)

    return f"""
You are resuming an OCD patient-analysis workflow for a therapist after receiving a clarification answer.

Your task:
Update the prior analysis using:
- the therapist's original request
- patient context
- therapist KB grounding
- the clarification question and therapist's answer

CRITICAL RULES:

1. Do not invent patient facts.
2. Use the therapist clarification answer as real additional context.
3. Revise the earlier analysis where needed.
4. Do not simply repeat the old analysis unchanged if the clarification changes interpretation.
5. Keep the analysis therapist-facing, not patient-facing.
6. Be thoughtful but avoid overclaiming.
7. analysis_summary should be cleaner and more presentation-ready than draft_analysis.
8. HARM OCD RULE: Intrusive harm thoughts in OCD patients are ego-dystonic symptoms — not genuine intent or actual risk. Do NOT treat harm-themed obsessions as real danger, do NOT recommend crisis measures based on OCD harm thoughts alone, and do NOT ask about ego-dystonicity unless the provided context explicitly contradicts typical OCD presentations.
9. PERSONALIZATION: All analysis must be grounded in the patient's actual obsessions, compulsions, fear ladder, and progress data provided below — do not speak generically when specific patient data is available.

Therapist current/original message:
{user_message}

Recent therapist chat context:
{recent_history_text}

Analysis goal:
{analysis_goal or "No explicit analysis goal provided."}

Patient context summary:
{patient_context_summary or "No patient context summary available."}

Latest weekly progress:
{weekly_progress_text}

Initial fear ladder:
{fear_ladder_text}

Obsession-compulsion pairs:
{erp_pairs_text}

Therapist KB grounding:
{kb_context_summary or "No therapist KB grounding available."}

Prior draft analysis:
{prior_draft_analysis or "No prior draft analysis available."}

Prior analysis summary:
{prior_analysis_summary or "No prior analysis summary available."}

Clarification question asked:
{clarification_question or "No clarification question available."}

Therapist clarification answer:
{clarification_answer}

Return structured output with:
- draft_analysis
- analysis_summary
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


def _format_weekly_progress(progress: Dict[str, Any] | None) -> str:
    if not progress:
        return "No weekly progress available."

    parts: List[str] = []

    week_number = progress.get("week_number")
    week_start_date = progress.get("week_start_date")
    detailed_progress = (progress.get("detailed_progress") or "").strip()
    homework_reflection = (progress.get("homework_reflection") or "").strip()
    suds_snapshot = progress.get("suds_snapshot")

    if week_number is not None:
        parts.append(f"week_number: {week_number}")
    if week_start_date:
        parts.append(f"week_start_date: {week_start_date}")
    if detailed_progress:
        parts.append(f"detailed_progress: {detailed_progress}")
    if homework_reflection:
        parts.append(f"homework_reflection: {homework_reflection}")
    if suds_snapshot:
        parts.append(f"suds_snapshot: {suds_snapshot}")

    return "\n".join(parts) if parts else "No weekly progress available."


def _format_fear_ladder(fear_ladder: Dict[str, Any] | None) -> str:
    if not fear_ladder:
        return "No initial fear ladder available."

    parts: List[str] = []

    status = fear_ladder.get("status")
    created_at = fear_ladder.get("created_at")
    items = fear_ladder.get("items") or []

    if status:
        parts.append(f"status: {status}")
    if created_at:
        parts.append(f"created_at: {created_at}")

    if items:
        item_lines = []
        for item in items[:12]:
            item_lines.append(
                f"- {item.get('item')} (SUDS: {item.get('suds')}, order: {item.get('order_index')})"
            )
        parts.append("items:\n" + "\n".join(item_lines))

    return "\n".join(parts) if parts else "No initial fear ladder available."


def _format_erp_pairs(pairs: List[Dict[str, Any]]) -> str:
    if not pairs:
        return "No obsession-compulsion pairs available."

    lines: List[str] = []

    for pair in pairs[:15]:
        obsession = (pair.get("obsession") or "").strip()
        compulsions = pair.get("compulsions") or []
        comp_text = ", ".join(str(c).strip() for c in compulsions if c and str(c).strip())

        if comp_text:
            lines.append(f"- Obsession: {obsession} | Compulsions: {comp_text}")
        else:
            lines.append(f"- Obsession: {obsession}")

    return "\n".join(lines)