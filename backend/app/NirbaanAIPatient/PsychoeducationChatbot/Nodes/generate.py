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
    - db_obsession_compulsion_pairs
    - db_latest_weekly_progress
    - session_context_summary
    - kb_chunks
    - web_used
    - web_results

    Outputs:
    - final_response
    - final_grounding_summary
    - used_sources
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    db_pairs = state.get("db_obsession_compulsion_pairs") or []
    db_latest_progress = state.get("db_latest_weekly_progress")
    kb_chunks = state.get("kb_chunks") or []
    web_used = bool(state.get("web_used", False))
    web_results = state.get("web_results") or []
    session_context_summary = (state.get("session_context_summary") or "").strip()

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
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
        kb_chunks=kb_chunks,
        web_results=web_results if has_web else [],
        session_context_summary=session_context_summary,
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
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.3-chat-latest"),
        
    )


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    db_pairs: List[Dict[str, Any]],
    db_latest_progress: Any,
    kb_chunks: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
    session_context_summary: str,
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    patient_context_text = _format_patient_context(
        db_pairs=db_pairs,
        db_latest_progress=db_latest_progress,
    )
    kb_text = _format_kb_chunks(kb_chunks)
    web_text = _format_web_results(web_results)

    return f"""
You are an OCD psychoeducation assistant for a therapy platform.

Your task:
Answer the patient's question clearly and helpfully using the provided grounded evidence.

Priority of evidence:
1. Therapist knowledge-base evidence is the highest priority.
2. Patient context may be used for personalization if relevant.
3. Web evidence is fallback only and should be used only if therapist KB evidence does not fully cover the point.

Rules:
1. Answer using only the provided grounded evidence.
2. Do not invent patient facts.
3. Do not claim certainty that is not supported by the evidence.
4. Keep the response psychoeducational, clear, and supportive.
5. Do not mention internal retrieval, nodes, databases, or tools.
6. Do not provide inappropriate reassurance.
7. If patient context is provided, use it to personalize naturally — reference the patient's actual listed obsessions and compulsions rather than speaking generically when their message clearly relates to their OCD profile.
8. If therapist KB and web evidence overlap, prefer therapist KB framing.
9. Do not cite raw URLs.
10. final_grounding_summary should briefly summarize what grounded the answer.
11. HARM OCD RULE: If the patient has harm-themed obsessions or asks about harm OCD, treat these as ego-dystonic OCD intrusive thoughts — NOT as genuine intent or actual risk. Do NOT treat the patient as a safety risk, do NOT suggest crisis lines or emergency services, and do NOT ask if they want to hurt themselves or others. Harm OCD involves unwanted intrusive thoughts that distress the patient because they conflict with their values. Respond with evidence-based psychoeducation about harm OCD as an OCD subtype.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Patient context (obsessions, compulsions, recent progress — use to personalize when relevant):
{patient_context_text}

Last therapy session context (relevant excerpt summary — use when relevant):
{session_context_summary if session_context_summary else "Not available."}

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


def _format_patient_context(
    *,
    db_pairs: List[Dict[str, Any]],
    db_latest_progress: Any,
) -> str:
    parts: List[str] = []

    if db_pairs:
        pair_lines: List[str] = []
        for pair in db_pairs:
            obsession = (pair.get("obsession") or "").strip()
            compulsions = pair.get("compulsions") or []
            comp_text = ", ".join(str(c).strip() for c in compulsions if c and str(c).strip())
            line = f"- Obsession: {obsession or 'N/A'}"
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