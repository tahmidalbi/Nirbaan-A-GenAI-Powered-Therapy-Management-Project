from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


class GenerateOutput(BaseModel):
    final_response: str = Field(
        ...,
        description="Final psychoeducation response for the patient."
    )
    final_grounding_summary: str = Field(
        default="",
        description="Compact summary of what evidence grounded the response."
    )


def generate_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Generate the final grounded psychoeducation answer.

    Inputs expected in state:
    - user_message
    - recent_chat_history
    - selected_obsession_compulsion_pairs
    - selected_progress_snippets
    - selected_db_context_summary
    - kb_chunks
    - kb_context_summary
    - web_used
    - web_results
    - web_context_summary

    Outputs:
    - final_response
    - final_grounding_summary
    - used_sources
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    selected_pairs = state.get("selected_obsession_compulsion_pairs") or []
    selected_progress_snippets = state.get("selected_progress_snippets") or []
    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()
    kb_chunks = state.get("kb_chunks") or []
    web_used = bool(state.get("web_used", False))
    web_results = state.get("web_results") or []
    selected_last_therapy_session = state.get("selected_last_therapy_session")

    if not user_message:
        return {
            "final_response": "I’m sorry, I couldn’t understand the question.",
            "final_grounding_summary": "",
            "used_sources": [],
        }

    has_kb = bool(kb_chunks)
    has_web = bool(web_used and web_results)

    if not has_kb and not has_web:
        return {
            "final_response": (
                "I don't have enough information to answer that well right now."
            ),
            "final_grounding_summary": "",
            "used_sources": [],
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(GenerateOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
        kb_chunks=kb_chunks,
        web_results=web_results if has_web else [],
        selected_last_therapy_session=selected_last_therapy_session,
    )

    result: GenerateOutput = structured_llm.invoke(prompt)

    final_response = (result.final_response or "").strip()
    if not final_response:
        final_response = "I don't have enough information to answer that well right now."

    final_grounding_summary = (result.final_grounding_summary or "").strip()
    used_sources = _build_used_sources(
        kb_chunks=kb_chunks,
        web_results=web_results if has_web else [],
    )

    return {
        "final_response": final_response,
        "final_grounding_summary": final_grounding_summary,
        "used_sources": used_sources,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2"),
        temperature=0.2,
    )


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    selected_pairs: List[Dict[str, Any]],
    selected_progress_snippets: List[str],
    selected_db_context_summary: str,
    kb_chunks: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
    selected_last_therapy_session: Dict[str, Any] | None,
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    db_context_text = _format_selected_db_context(
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
    )
    kb_text = _format_kb_chunks(kb_chunks)
    web_text = _format_web_results(web_results)

    if selected_last_therapy_session:
        session_text = (
            f"Session {selected_last_therapy_session.get('session_number', '?')}"
            f" — {selected_last_therapy_session.get('title', '')}"
            f" ({selected_last_therapy_session.get('session_date', '')})"
            f"\n{selected_last_therapy_session.get('transcript', '')}"
        ).strip()
    else:
        session_text = "Not included."

    return f"""
You are an OCD psychoeducation assistant for a therapy platform.

Your task:
Answer the patient's question clearly and helpfully using the provided grounded evidence.

Priority of evidence:
1. Therapist knowledge-base evidence is the highest priority.
2. Selected patient DB context may be used for personalization if relevant.
3. Web evidence is fallback only and should be used only if therapist KB evidence does not fully cover the point.

Rules:
1. Answer using only the provided grounded evidence.
2. Do not invent patient facts.
3. Do not claim certainty that is not supported by the evidence.
4. Keep the response psychoeducational, clear, and supportive.
5. Do not mention internal retrieval, nodes, databases, or tools.
6. Do not provide inappropriate reassurance.
7. If patient-specific context was selected, use it lightly and relevantly.
8. If therapist KB and web evidence overlap, prefer therapist KB framing.
9. Do not cite raw URLs.
10. final_grounding_summary should briefly summarize what grounded the answer.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Selected patient DB context:
{db_context_text}

Last therapy session:
{session_text}

Therapist KB evidence:
{kb_text}

Web fallback evidence:
{web_text}

Return structured output with:
- final_response
- final_grounding_summary
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
        return "No therapist KB evidence available."

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
            f"[KB Source {idx}: {source}{location_suffix}]\n{content}"
        )

    return "\n\n---\n\n".join(parts)


def _format_web_results(web_results: List[Dict[str, Any]]) -> str:
    if not web_results:
        return "No web fallback evidence available."

    parts: List[str] = []

    for idx, result in enumerate(web_results, start=1):
        title = (result.get("title") or "Untitled").strip()
        source = (result.get("source") or "unknown").strip()
        content = (result.get("content") or "").strip()

        parts.append(
            f"[Web Source {idx}: {title} ({source})]\n{content}"
        )

    return "\n\n---\n\n".join(parts)


def _build_used_sources(
    *,
    kb_chunks: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
) -> List[str]:
    sources: List[str] = []
    seen = set()

    for chunk in kb_chunks:
        source = (chunk.get("source") or "").strip()
        if source and source not in seen:
            sources.append(source)
            seen.add(source)

    for result in web_results:
        title = (result.get("title") or "").strip()
        source = (result.get("source") or "").strip()

        label = title if title else source
        if label and label not in seen:
            sources.append(label)
            seen.add(label)

    return sources