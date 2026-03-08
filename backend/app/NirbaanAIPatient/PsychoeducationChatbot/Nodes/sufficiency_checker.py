from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


class SufficiencyCheckOutput(BaseModel):
    retrieval_sufficient: bool = Field(
        ...,
        description="Whether the currently retrieved evidence is sufficient to answer the patient's question well."
    )
    insufficiency_reason: str = Field(
        default="",
        description="Why the current evidence is insufficient, if it is insufficient."
    )
    missing_concept: str = Field(
        default="",
        description="The main missing concept that the next retrieval should try to find."
    )


def sufficiency_checker_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Judge whether the current selected DB context + retrieved KB chunks are enough
    to answer the patient's question.

    Inputs expected in state:
    - user_message
    - recent_chat_history
    - selected_obsession_compulsion_pairs
    - selected_progress_snippets
    - selected_db_context_summary
    - kb_chunks
    - kb_context_summary

    Outputs:
    - retrieval_sufficient
    - insufficiency_reason
    - missing_concept
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    selected_pairs = state.get("selected_obsession_compulsion_pairs") or []
    selected_progress_snippets = state.get("selected_progress_snippets") or []
    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()
    kb_chunks = state.get("kb_chunks") or []

    if not user_message:
        return {
            "retrieval_sufficient": False,
            "insufficiency_reason": "No user message was provided.",
            "missing_concept": "patient question",
        }

    if not kb_chunks:
        return {
            "retrieval_sufficient": False,
            "insufficiency_reason": "No therapist knowledge-base chunks were retrieved.",
            "missing_concept": user_message,
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(SufficiencyCheckOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
        kb_chunks=kb_chunks,
    )

    result: SufficiencyCheckOutput = structured_llm.invoke(prompt)

    return {
        "retrieval_sufficient": bool(result.retrieval_sufficient),
        "insufficiency_reason": (result.insufficiency_reason or "").strip(),
        "missing_concept": (result.missing_concept or "").strip(),
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
    selected_pairs: List[Dict[str, Any]],
    selected_progress_snippets: List[str],
    selected_db_context_summary: str,
    kb_chunks: List[Dict[str, Any]],
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    selected_db_text = _format_selected_db_context(
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
    )
    kb_chunks_text = _format_kb_chunks(kb_chunks)

    return f"""
You are checking whether the currently retrieved evidence is sufficient for an OCD psychoeducation chatbot to answer a patient well.

Your task is NOT to answer the patient.
Your task is ONLY to judge whether the current evidence is enough.

Evidence available:
1. Selected patient-specific database context
2. Retrieved therapist knowledge-base chunks

Decision rules:
1. Mark retrieval_sufficient=true only if the current evidence is enough to answer the patient's actual question clearly and groundedly.
2. If the evidence is too generic, off-topic, incomplete, or misses an important concept, mark retrieval_sufficient=false.
3. If insufficient, explain briefly what is missing.
4. If insufficient, provide a short missing_concept phrase that will help improve the next retrieval query.
5. Do not invent missing patient facts.
6. Be strict. It is better to trigger another retrieval than to pretend weak evidence is enough.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Selected patient DB context:
{selected_db_text}

Retrieved therapist KB chunks:
{kb_chunks_text}

Return structured output with:
- retrieval_sufficient
- insufficiency_reason
- missing_concept
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


def _format_selected_db_context(
    *,
    selected_pairs: List[Dict[str, Any]],
    selected_progress_snippets: List[str],
    selected_db_context_summary: str,
) -> str:
    parts: List[str] = []

    if selected_pairs:
        pair_lines: List[str] = []
        for pair in selected_pairs:
            erp_item_id = pair.get("erp_item_id")
            obsession = (pair.get("obsession") or "").strip()
            compulsions = pair.get("compulsions") or []
            comp_text = ", ".join(str(c).strip() for c in compulsions if c and str(c).strip())

            line = f"- erp_item_id: {erp_item_id} | obsession: {obsession or 'N/A'}"
            if comp_text:
                line += f" | compulsions: {comp_text}"
            pair_lines.append(line)

        parts.append("Selected obsession-compulsion pairs:\n" + "\n".join(pair_lines))

    if selected_progress_snippets:
        parts.append("Selected latest progress report:\n" + "\n".join(f"- {x}" for x in selected_progress_snippets))

    if selected_db_context_summary:
        parts.append(f"Why this DB context was selected:\n- {selected_db_context_summary}")

    return "\n\n".join(parts).strip() if parts else "No selected patient DB context."


def _format_kb_chunks(kb_chunks: List[Dict[str, Any]]) -> str:
    if not kb_chunks:
        return "No KB chunks retrieved."

    parts: List[str] = []

    for idx, chunk in enumerate(kb_chunks, start=1):
        content = (chunk.get("content") or "").strip()
        source = (chunk.get("source") or "Untitled").strip()
        metadata = chunk.get("metadata") or {}

        location_bits: List[str] = []

        source_type = metadata.get("source_type")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        if source_type:
            location_bits.append(str(source_type))

        if page_start and page_end:
            if page_start == page_end:
                location_bits.append(f"page {page_start}")
            else:
                location_bits.append(f"pages {page_start}-{page_end}")
        elif page_start:
            location_bits.append(f"page {page_start}")

        location_suffix = f" ({', '.join(location_bits)})" if location_bits else ""

        parts.append(
            f"[KB Chunk {idx}: {source}{location_suffix}]\n{content}"
        )

    return "\n\n---\n\n".join(parts)