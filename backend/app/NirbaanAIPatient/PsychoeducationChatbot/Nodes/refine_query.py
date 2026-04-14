from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


class RefineQueryOutput(BaseModel):
    refined_query: str = Field(
        ...,
        description="An improved retrieval query for therapist KB search."
    )


def refine_query_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Refine the retrieval query when current KB evidence is insufficient.

    Inputs expected in state:
    - user_message
    - recent_chat_history
    - selected_obsession_compulsion_pairs
    - selected_progress_snippets
    - selected_db_context_summary
    - retrieval_query
    - original_retrieval_query
    - refined_query_history
    - insufficiency_reason
    - missing_concept
    - retry_count

    Outputs:
    - retrieval_query
    - refined_query_history
    - retry_count
    """
    user_message = (state.get("user_message") or "").strip()
    current_query = (state.get("retrieval_query") or "").strip()
    original_query = (state.get("original_retrieval_query") or "").strip()
    refined_query_history = list(state.get("refined_query_history") or [])
    recent_chat_history = state.get("recent_chat_history") or []
    selected_pairs = state.get("selected_obsession_compulsion_pairs") or []
    selected_progress_snippets = state.get("selected_progress_snippets") or []
    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()
    insufficiency_reason = (state.get("insufficiency_reason") or "").strip()
    missing_concept = (state.get("missing_concept") or "").strip()
    retry_count = int(state.get("retry_count", 0))

    if not user_message:
        return {
            "retrieval_query": current_query,
            "refined_query_history": refined_query_history,
            "retry_count": retry_count + 1,
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(RefineQueryOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
        current_query=current_query,
        original_query=original_query,
        previous_refined_queries=refined_query_history,
        insufficiency_reason=insufficiency_reason,
        missing_concept=missing_concept,
    )

    result: RefineQueryOutput = structured_llm.invoke(prompt)

    new_query = (result.refined_query or "").strip()
    if not new_query:
        new_query = current_query or original_query or user_message

    updated_history = refined_query_history + [new_query]

    return {
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
    selected_pairs: List[Dict[str, Any]],
    selected_progress_snippets: List[str],
    selected_db_context_summary: str,
    current_query: str,
    original_query: str,
    previous_refined_queries: List[str],
    insufficiency_reason: str,
    missing_concept: str,
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    selected_db_text = _format_selected_db_context(
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
    )
    previous_queries_text = _format_previous_queries(previous_refined_queries)

    return f"""
You are improving a retrieval query for an OCD psychoeducation chatbot.

Your task is NOT to answer the patient.
Your task is ONLY to write a better therapist-KB retrieval query.

Goal:
Rewrite the retrieval query so the next KB search is more likely to find material that answers the patient's actual question.

Rules:
1. Focus on the missing concept and insufficiency reason.
2. Keep the query semantically rich, clear, and retrieval-friendly.
3. Use OCD / ERP terminology when helpful.
4. Do not write a conversational answer.
5. Do not invent patient facts.
6. Do not simply repeat the current query if it can be improved.
7. The output should be a single improved query string.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Selected patient DB context:
{selected_db_text}

Original retrieval query:
{original_query}

Current retrieval query:
{current_query}

Previous refined queries:
{previous_queries_text}

Why current retrieval was insufficient:
{insufficiency_reason or "No insufficiency reason provided."}

Main missing concept to retrieve:
{missing_concept or "No missing concept provided."}

Return structured output with:
- refined_query
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


def _format_previous_queries(previous_refined_queries: List[str]) -> str:
    if not previous_refined_queries:
        return "None."

    return "\n".join(f"- {q}" for q in previous_refined_queries)