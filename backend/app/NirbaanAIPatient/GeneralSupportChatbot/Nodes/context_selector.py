from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState


class ContextSelectorOutput(BaseModel):
    needs_personalization: bool = Field(
        ...,
        description="Whether patient-specific DB context should be included."
    )
    selected_erp_item_ids: List[int] = Field(
        default_factory=list,
        description="IDs of the relevant ERP items from the provided list."
    )
    include_latest_progress_report: bool = Field(
        default=False,
        description="Whether the full latest weekly progress report should be included."
    )
    include_last_therapy_session: bool = Field(
        default=False,
        description="Whether the last therapy session transcript should be included."
    )
    support_type: str = Field(
        ...,
        description=(
            "One of: emotional_distress, erp_burnout, reassurance_seeking, "
            "intrusive_thought_spike, motivation_loss, general_stress, other"
        ),
    )
    support_goal: str = Field(
        default="",
        description="Short description of the support objective for downstream nodes."
    )
    selected_db_context_summary: str = Field(
        default="",
        description="Compact explanation of why the selected DB context is relevant."
    )


def context_selector_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    LLM-based selector for relevant patient DB context for the general support graph.

    Inputs expected in state:
    - user_message
    - recent_chat_history
    - db_obsession_compulsion_pairs
    - db_latest_weekly_progress

    Outputs:
    - needs_personalization
    - selected_obsession_compulsion_pairs
    - selected_progress_snippets
    - selected_db_context_summary
    - support_type
    - support_goal
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    db_pairs = state.get("db_obsession_compulsion_pairs") or []
    latest_progress = state.get("db_latest_weekly_progress")
    db_last_therapy_session = state.get("db_last_therapy_session")

    if not user_message:
        return {
            "needs_personalization": False,
            "selected_obsession_compulsion_pairs": [],
            "selected_progress_snippets": [],
            "selected_db_context_summary": "",
            "selected_last_therapy_session": None,
            "support_type": "other",
            "support_goal": "",
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(ContextSelectorOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        db_pairs=db_pairs,
        latest_progress=latest_progress,
        last_therapy_session=db_last_therapy_session,
    )

    result: ContextSelectorOutput = structured_llm.invoke(prompt)

    selected_pairs = _map_selected_pairs(
        selected_ids=result.selected_erp_item_ids,
        db_pairs=db_pairs,
    )

    selected_progress_snippets = _build_selected_progress_snippets(
        include_latest_progress_report=result.include_latest_progress_report,
        latest_progress=latest_progress,
    )

    selected_last_therapy_session = db_last_therapy_session if result.include_last_therapy_session else None

    actually_needs_personalization = bool(
        result.needs_personalization and (selected_pairs or selected_progress_snippets or selected_last_therapy_session)
    )

    support_type = _normalize_support_type(result.support_type)
    support_goal = (result.support_goal or "").strip()
    selected_db_context_summary = (result.selected_db_context_summary or "").strip()

    return {
        "needs_personalization": actually_needs_personalization,
        "selected_obsession_compulsion_pairs": selected_pairs,
        "selected_progress_snippets": selected_progress_snippets,
        "selected_db_context_summary": selected_db_context_summary,
        "selected_last_therapy_session": selected_last_therapy_session,
        "support_type": support_type,
        "support_goal": support_goal,
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
    db_pairs: List[Dict[str, Any]],
    latest_progress: Optional[Dict[str, Any]],
    last_therapy_session: Optional[Dict[str, Any]],
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    erp_pairs_text = _format_erp_pairs(db_pairs)
    weekly_progress_text = _format_weekly_progress(latest_progress)
    last_session_text = _format_last_therapy_session(last_therapy_session)

    return f"""
You are selecting patient-specific database context for an OCD between-session general support chatbot.

Your task is NOT to answer the patient.
Your task is ONLY to:
1. identify the support type,
2. identify the support goal,
3. decide whether personalization is needed,
4. choose which structured DB context should be included.

Rules:
1. Select patient context only if it will meaningfully improve the support response.
2. If the message is broad emotional support and patient-specific data is not needed, select nothing.
3. Never invent patient facts.
4. Only choose ERP item IDs that are explicitly provided below.
5. If you choose an ERP item, the full obsession-compulsion pair for that item will be included later.
6. If you set include_latest_progress_report=true, the full latest weekly progress report will be included later.
7. Keep the selection minimal and relevant.
8. Prefer fewer ERP items over too many items.
9. The support_type must be one of:
   - emotional_distress
   - erp_burnout
   - reassurance_seeking
   - intrusive_thought_spike
   - motivation_loss
   - general_stress
   - other
10. support_goal should be one short grounded sentence describing the kind of support needed.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Available ERP obsession-compulsion pairs:
{erp_pairs_text}

Latest weekly progress:
{weekly_progress_text}

Last therapy session:
{last_session_text}

Return structured output with:
- needs_personalization
- selected_erp_item_ids
- include_latest_progress_report
- include_last_therapy_session
- support_type
- support_goal
- selected_db_context_summary
""".strip()


def _format_recent_chat_history(recent_chat_history: List[Dict[str, str]]) -> str:
    if not recent_chat_history:
        return "No recent chat history."

    lines: List[str] = []
    for msg in recent_chat_history[-6:]:
        role = (msg.get("role") or "unknown").strip()
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No recent chat history."


def _format_erp_pairs(db_pairs: List[Dict[str, Any]]) -> str:
    if not db_pairs:
        return "No ERP items available."

    blocks: List[str] = []

    for pair in db_pairs:
        erp_item_id = pair.get("erp_item_id")
        obsession = (pair.get("obsession") or "").strip()
        compulsions = pair.get("compulsions") or []

        comp_text = ", ".join(str(c).strip() for c in compulsions if c and str(c).strip())

        block = f"- erp_item_id: {erp_item_id}\n  obsession: {obsession or 'N/A'}"
        if comp_text:
            block += f"\n  compulsions: {comp_text}"
        else:
            block += "\n  compulsions: none listed"

        blocks.append(block)

    return "\n".join(blocks)


def _format_weekly_progress(latest_progress: Optional[Dict[str, Any]]) -> str:
    if not latest_progress:
        return "No weekly progress available."

    week_number = latest_progress.get("week_number")
    week_start_date = latest_progress.get("week_start_date")
    detailed_progress = (latest_progress.get("detailed_progress") or "").strip()
    homework_reflection = (latest_progress.get("homework_reflection") or "").strip()
    suds_snapshot = latest_progress.get("suds_snapshot")

    parts = [
        f"week_number: {week_number}",
        f"week_start_date: {week_start_date}",
        f"detailed_progress: {detailed_progress or 'N/A'}",
        f"homework_reflection: {homework_reflection or 'N/A'}",
    ]

    if suds_snapshot:
        parts.append(f"suds_snapshot: {suds_snapshot}")

    return "\n".join(parts)


def _format_last_therapy_session(last_therapy_session: Optional[Dict[str, Any]]) -> str:
    if not last_therapy_session:
        return "No therapy session available."

    session_number = last_therapy_session.get("session_number", "?")
    title = (last_therapy_session.get("title") or "").strip()
    session_date = last_therapy_session.get("session_date", "")
    transcript = (last_therapy_session.get("transcript") or "").strip()

    lines = [
        f"session_number: {session_number}",
        f"title: {title or 'N/A'}",
        f"session_date: {session_date}",
        f"transcript: {transcript[:500]}{'...' if len(transcript) > 500 else ''}",
    ]
    return "\n".join(lines)


def _map_selected_pairs(
    *,
    selected_ids: List[int],
    db_pairs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not selected_ids:
        return []

    try:
        id_set = {int(x) for x in selected_ids}
    except Exception:
        return []

    selected = [pair for pair in db_pairs if pair.get("erp_item_id") in id_set]

    order_map = {erp_id: idx for idx, erp_id in enumerate(selected_ids)}
    selected.sort(key=lambda x: order_map.get(x.get("erp_item_id"), 9999))

    return selected[:3]


def _build_selected_progress_snippets(
    *,
    include_latest_progress_report: bool,
    latest_progress: Optional[Dict[str, Any]],
) -> List[str]:
    """
    Keeps state unchanged while allowing the entire latest progress report
    to be included through selected_progress_snippets as one full string.
    """
    if not include_latest_progress_report or not latest_progress:
        return []

    progress_parts: List[str] = []

    week_number = latest_progress.get("week_number")
    week_start_date = latest_progress.get("week_start_date")
    detailed_progress = (latest_progress.get("detailed_progress") or "").strip()
    homework_reflection = (latest_progress.get("homework_reflection") or "").strip()
    suds_snapshot = latest_progress.get("suds_snapshot")

    if week_number is not None:
        progress_parts.append(f"week_number: {week_number}")
    if week_start_date:
        progress_parts.append(f"week_start_date: {week_start_date}")
    if detailed_progress:
        progress_parts.append(f"detailed_progress: {detailed_progress}")
    if homework_reflection:
        progress_parts.append(f"homework_reflection: {homework_reflection}")
    if suds_snapshot:
        progress_parts.append(f"suds_snapshot: {suds_snapshot}")

    if not progress_parts:
        return []

    return [" | ".join(progress_parts)]


def _normalize_support_type(value: str) -> str:
    allowed = {
        "emotional_distress",
        "erp_burnout",
        "reassurance_seeking",
        "intrusive_thought_spike",
        "motivation_loss",
        "general_stress",
        "other",
    }
    value = (value or "").strip()
    return value if value in allowed else "other"