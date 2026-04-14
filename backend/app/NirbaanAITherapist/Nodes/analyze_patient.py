from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAITherapist.state import NirbaanAITherapistState


class AnalyzePatientOutput(BaseModel):
    draft_analysis: str = Field(
        ...,
        description="Internal fuller patient analysis draft."
    )
    analysis_summary: str = Field(
        ...,
        description="Clean therapist-facing analysis summary."
    )
    needs_clarification: bool = Field(
        ...,
        description="Whether one therapist clarification is needed before finalizing the analysis."
    )
    clarification_question: str = Field(
        default="",
        description="A single concise clarification question for the therapist if clarification is needed."
    )


def analyze_patient_node(state: NirbaanAITherapistState) -> Dict[str, Any]:
    """
    Analyze the patient using:
    - therapist chat question
    - recent therapist chat history
    - loaded patient context
    - therapist KB retrieval

    This node also decides whether clarification is needed.
    """

    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []

    analysis_goal = (state.get("analysis_goal") or "").strip()

    patient_context_summary = (state.get("patient_context_summary") or "").strip()
    latest_weekly_progress = state.get("latest_weekly_progress")
    initial_fear_ladder = state.get("initial_fear_ladder")
    obsession_compulsion_pairs = state.get("obsession_compulsion_pairs") or []

    kb_context_summary = (state.get("kb_context_summary") or "").strip()
    kb_chunks = state.get("kb_chunks") or []

    llm = _get_llm()
    structured_llm = llm.with_structured_output(AnalyzePatientOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        analysis_goal=analysis_goal,
        patient_context_summary=patient_context_summary,
        latest_weekly_progress=latest_weekly_progress,
        initial_fear_ladder=initial_fear_ladder,
        obsession_compulsion_pairs=obsession_compulsion_pairs,
        kb_context_summary=kb_context_summary,
    )

    result: AnalyzePatientOutput = structured_llm.invoke(prompt)

    used_sources = _collect_sources(kb_chunks)
    needs_clarification = bool(result.needs_clarification)
    clarification_question = (result.clarification_question or "").strip()

    if not needs_clarification:
        clarification_question = ""

    return {
        "draft_analysis": (result.draft_analysis or "").strip(),
        "analysis_summary": (result.analysis_summary or "").strip(),
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "used_sources": used_sources,
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
) -> str:
    recent_history_text = _format_chat_history(recent_chat_history)
    weekly_progress_text = _format_weekly_progress(latest_weekly_progress)
    fear_ladder_text = _format_fear_ladder(initial_fear_ladder)
    erp_pairs_text = _format_erp_pairs(obsession_compulsion_pairs)

    return f"""
You are an AI assistant helping a therapist analyze a patient with OCD.

Your task:
Study the patient using:
- the therapist's current question
- recent therapist chat context
- patient progress/context
- therapist knowledge base guidance

You must do two things:
1. Produce a strong therapist-facing analysis.
2. Decide whether one clarification question is needed before the analysis should be finalized.

CRITICAL RULES:

1. Do not invent patient facts.
2. Ground analysis in the provided patient context and therapist KB.
3. If something is uncertain, state it as uncertainty rather than pretending confidence.
4. Do not provide reassurance-oriented patient-facing language.
5. This is therapist-facing analysis, not a direct patient response.
6. Use the therapist's KB as guidance when relevant.
7. Be clinically thoughtful but not overclaiming.
8. The analysis_summary should be cleaner and more presentation-ready than draft_analysis.
9. Only ask for clarification if one missing therapist judgment/detail would materially improve the analysis.
10. Ask at most one concise, high-value clarification question.
11. If clarification is not needed, set clarification_question to an empty string.
12. Prefer finalizing the analysis unless the missing detail would meaningfully change formulation or recommendation.
13. If relevant patient information already exists in the provided context (such as ERP obsession-compulsion pairs, fear ladder items, or weekly progress), do not ask clarification questions that simply repeat or request the same information.
14. HARM OCD RULE: In patients already undergoing ERP treatment for OCD, assume intrusive harm thoughts are ego-dystonic OCD symptoms — not genuine intent, not a real safety risk, and not indicative of actual danger. Do NOT ask clarification questions about whether the thoughts are ego-dystonic, do NOT suggest the patient may be a safety risk, and do NOT recommend crisis interventions based on harm OCD alone unless the context explicitly describes behavior (not just thoughts) that is uncharacteristic of OCD. Analyzing harm OCD is a routine clinical task.
15. PERSONALIZATION: The patient's specific obsessions, compulsions, fear ladder, and progress are provided. All analysis must be grounded in and reference the patient's actual profile — do not speak generically when their specific data is available.

Therapist current message:
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

Return structured output with:
- draft_analysis
- analysis_summary
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