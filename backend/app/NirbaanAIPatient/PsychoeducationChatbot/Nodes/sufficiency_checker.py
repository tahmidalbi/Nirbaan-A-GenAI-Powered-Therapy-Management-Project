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
    refined_query: str = Field(
        default="",
        description="An improved retrieval query to use if retrieval is insufficient. Leave empty if retrieval is sufficient."
    )


def sufficiency_checker_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Judge whether the retrieved KB chunks are enough to answer the patient's question.
    If insufficient, also produces a refined retrieval query for the next KB search.

    Inputs expected in state:
    - user_message
    - recent_chat_history
    - db_obsession_compulsion_pairs
    - kb_chunks
    - retrieval_query
    - original_retrieval_query
    - refined_query_history
    - retry_count

    Outputs:
    - retrieval_sufficient
    - insufficiency_reason
    - missing_concept
    - retrieval_query  (updated to refined query when insufficient)
    - refined_query_history
    - retry_count
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    db_pairs = state.get("db_obsession_compulsion_pairs") or []
    kb_chunks = state.get("kb_chunks") or []
    current_query = (state.get("retrieval_query") or "").strip()
    original_query = (state.get("original_retrieval_query") or "").strip()
    refined_query_history = list(state.get("refined_query_history") or [])
    retry_count = int(state.get("retry_count", 0))

    if not user_message:
        return {
            "retrieval_sufficient": False,
            "insufficiency_reason": "No user message was provided.",
            "missing_concept": "patient question",
            "retrieval_query": current_query,
            "refined_query_history": refined_query_history,
            "retry_count": retry_count + 1,
        }

    if not kb_chunks:
        return {
            "retrieval_sufficient": False,
            "insufficiency_reason": "No therapist knowledge-base chunks were retrieved.",
            "missing_concept": user_message,
            "retrieval_query": current_query,
            "refined_query_history": refined_query_history,
            "retry_count": retry_count + 1,
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(SufficiencyCheckOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        db_pairs=db_pairs,
        kb_chunks=kb_chunks,
        current_query=current_query,
        original_query=original_query,
        refined_query_history=refined_query_history,
    )

    result: SufficiencyCheckOutput = structured_llm.invoke(prompt)

    if bool(result.retrieval_sufficient):
        return {
            "retrieval_sufficient": True,
            "insufficiency_reason": "",
            "missing_concept": "",
            "retrieval_query": current_query,
            "refined_query_history": refined_query_history,
            "retry_count": retry_count,
        }

    # Insufficient: apply the refined query produced in this same LLM call
    new_query = (result.refined_query or "").strip()
    if not new_query:
        new_query = current_query or original_query or user_message

    updated_history = refined_query_history + [new_query]

    return {
        "retrieval_sufficient": False,
        "insufficiency_reason": (result.insufficiency_reason or "").strip(),
        "missing_concept": (result.missing_concept or "").strip(),
        "retrieval_query": new_query,
        "refined_query_history": updated_history,
        "retry_count": retry_count + 1,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.3-chat-latest"),
    )


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    db_pairs: List[Dict[str, Any]],
    kb_chunks: List[Dict[str, Any]],
    current_query: str,
    original_query: str,
    refined_query_history: List[str],
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    patient_context_text = _format_patient_context(db_pairs=db_pairs)
    kb_chunks_text = _format_kb_chunks(kb_chunks)
    previous_queries_text = (
        "\n".join(f"- {q}" for q in refined_query_history) if refined_query_history else "None"
    )

    return f"""
You are checking whether the currently retrieved evidence is sufficient for an OCD psychoeducation chatbot to answer a patient well.

Your task is NOT to answer the patient.
Your task is ONLY to judge whether the current evidence is enough, and if not, produce an improved retrieval query.

Evidence available:
1. Patient context (obsession-compulsion pairs)
2. Retrieved therapist knowledge-base chunks

Decision rules:
1. Mark retrieval_sufficient=true only if the current evidence is enough to answer the patient's actual question clearly and groundedly.
2. If the evidence is too generic, off-topic, incomplete, or misses an important concept, mark retrieval_sufficient=false.
3. If insufficient, explain briefly what is missing.
4. If insufficient, provide a short missing_concept phrase that will help improve the next retrieval query.
5. If insufficient, write a refined_query: an improved, semantically rich retrieval query focused on the missing concept. Use OCD/ERP terminology when helpful. Do not repeat a previous query.
6. If sufficient, leave refined_query empty.
7. Do not invent missing patient facts.
8. Be strict. It is better to trigger another retrieval than to pretend weak evidence is enough.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Patient context (obsession-compulsion pairs):
{patient_context_text}

Retrieved therapist KB chunks:
{kb_chunks_text}

Original retrieval query:
{original_query or current_query}

Current retrieval query:
{current_query}

Previous refined queries:
{previous_queries_text}

Return structured output with:
- retrieval_sufficient
- insufficiency_reason
- missing_concept
- refined_query (only when retrieval_sufficient=false)
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


def _format_patient_context(*, db_pairs: List[Dict[str, Any]]) -> str:
    if not db_pairs:
        return "No patient context available."

    pair_lines: List[str] = []
    for pair in db_pairs:
        obsession = (pair.get("obsession") or "").strip()
        compulsions = pair.get("compulsions") or []
        comp_text = ", ".join(str(c).strip() for c in compulsions if c and str(c).strip())
        line = f"- Obsession: {obsession or 'N/A'}"
        if comp_text:
            line += f" | Compulsions: {comp_text}"
        pair_lines.append(line)

    return "Obsession-compulsion pairs:\n" + "\n".join(pair_lines)


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