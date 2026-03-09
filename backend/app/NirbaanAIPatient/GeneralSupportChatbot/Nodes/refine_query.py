from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState


class RefineQueryOutput(BaseModel):
    retrieval_query: str = Field(
        ...,
        description="A keyword-rich, declarative retrieval query optimized for vector similarity search."
    )


def refine_query_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Build a strong retrieval query for general support messages.
    """
    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []
    selected_pairs = state.get("selected_obsession_compulsion_pairs") or []
    selected_progress_snippets = state.get("selected_progress_snippets") or []
    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()
    support_type = (state.get("support_type") or "other").strip()
    support_goal = (state.get("support_goal") or "").strip()

    if not user_message:
        return {
            "retrieval_query": "",
            "original_retrieval_query": "",
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(RefineQueryOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
        support_type=support_type,
        support_goal=support_goal,
    )

    result: RefineQueryOutput = structured_llm.invoke(prompt)

    retrieval_query = (result.retrieval_query or "").strip()
    if not retrieval_query:
        retrieval_query = user_message

    return {
        "retrieval_query": retrieval_query,
        "original_retrieval_query": retrieval_query,
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
    support_type: str,
    support_goal: str,
) -> str:
    recent_history_text = _format_recent_chat_history(recent_chat_history)
    selected_db_text = _format_selected_db_context(
        selected_pairs=selected_pairs,
        selected_progress_snippets=selected_progress_snippets,
        selected_db_context_summary=selected_db_context_summary,
    )

    return f"""
You are an AI assistant optimizing queries for a vector database containing therapist knowledge base documents and clinical guidelines for OCD treatment.

Your task is NOT to answer the patient.
Your task is ONLY to convert the patient's vague support message into a strong, declarative, keyword-rich retrieval query.

Vector similarity search works best when the query semantically matches the tone, phrasing, and terminology of clinical manuals.
Instead of conversational questions (e.g., "What to say if the patient feels down"), generate conceptual, clinical queries.

Examples:
- Patient: "I'm feeling down" -> Query: "between-session support interventions for low mood and depressive symptoms in OCD patients"
- Patient: "I can't stop checking the stove" -> Query: "ERP response prevention strategies for checking compulsions and doubting obsessions"
- Patient: "I just need to know it will be okay" -> Query: "therapist guidance on avoiding reassurance and encouraging tolerance of uncertainty"

Goal:
Write a retrieval-friendly, keyword-rich query that will help find therapist guidance relevant to the patient's current support need.

Rules:
1. The query should reflect the support_type and support_goal.
2. Use clinical OCD / ERP terminology (e.g., "response prevention", "tolerance of uncertainty", "intrusive thoughts").
3. If selected patient context is relevant, incorporate it naturally into the retrieval query.
4. Do not invent patient facts.
5. Do not write a supportive response.
6. Output a single retrieval query string.
7. Maximize semantic richness for cosine similarity matching against clinical texts.

Patient current message:
{user_message}

Recent chat history:
{recent_history_text}

Support type:
{support_type}

Support goal:
{support_goal or "Not provided."}

Selected patient DB context:
{selected_db_text}

Return structured output with:
- retrieval_query
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

            comp_text = ", ".join(
                str(c).strip()
                for c in compulsions
                if c and str(c).strip()
            )

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