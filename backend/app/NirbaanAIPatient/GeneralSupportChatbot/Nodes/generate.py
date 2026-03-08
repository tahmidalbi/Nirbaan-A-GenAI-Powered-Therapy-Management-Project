from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState


class GenerateOutput(BaseModel):
    final_response: str = Field(..., description="Final support message to patient.")


def generate_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Generate the final grounded support response.
    """

    user_message = (state.get("user_message") or "").strip()
    recent_chat_history = state.get("recent_chat_history") or []

    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()
    kb_context_summary = (state.get("kb_context_summary") or "").strip()
    web_context_summary = (state.get("web_context_summary") or "").strip()

    support_type = (state.get("support_type") or "other").strip()
    support_goal = (state.get("support_goal") or "").strip()

    web_used = state.get("web_used", False)

    grounding_context = _build_grounding_context(
        kb_context_summary,
        web_context_summary,
    )

    used_sources = _collect_sources(
        state.get("kb_chunks") or [],
        state.get("web_results") or [],
    )

    llm = _get_llm()
    structured_llm = llm.with_structured_output(GenerateOutput)

    prompt = _build_prompt(
        user_message=user_message,
        recent_chat_history=recent_chat_history,
        selected_db_context_summary=selected_db_context_summary,
        grounding_context=grounding_context,
        support_type=support_type,
        support_goal=support_goal,
        web_used=web_used,
    )

    result: GenerateOutput = structured_llm.invoke(prompt)

    return {
        "final_response": result.final_response.strip(),
        "used_sources": used_sources,
        "final_grounding_summary": grounding_context,
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2"),
        temperature=0.4,
    )


def _build_grounding_context(
    kb_context_summary: str,
    web_context_summary: str,
) -> str:

    if kb_context_summary and web_context_summary:
        return kb_context_summary + "\n\n---\n\n" + web_context_summary

    if kb_context_summary:
        return kb_context_summary

    if web_context_summary:
        return web_context_summary

    return ""


def _collect_sources(
    kb_chunks: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
) -> List[str]:

    sources: List[str] = []

    for c in kb_chunks:
        src = c.get("source")
        if src and src not in sources:
            sources.append(src)

    for r in web_results:
        src = r.get("url")
        if src and src not in sources:
            sources.append(src)

    return sources


def _build_prompt(
    *,
    user_message: str,
    recent_chat_history: List[Dict[str, str]],
    selected_db_context_summary: str,
    grounding_context: str,
    support_type: str,
    support_goal: str,
    web_used: bool,
) -> str:

    recent_history_text = _format_chat_history(recent_chat_history)

    return f"""
You are a supportive OCD therapy assistant helping a patient between therapy sessions.

Your role is to provide grounded support consistent with OCD treatment principles.

CRITICAL RULES:

1. DO NOT provide reassurance about feared outcomes.
2. DO NOT guarantee safety or certainty.
3. DO NOT help the patient neutralize intrusive thoughts.
4. Encourage tolerance of uncertainty.
5. Encourage response prevention rather than rituals.
6. Validate emotional difficulty without validating OCD fears.
7. Focus on coping, perspective, and sustainable steps.

Support type:
{support_type}

Support goal:
{support_goal}

Patient message:
{user_message}

Recent conversation:
{recent_history_text}

Relevant patient context:
{selected_db_context_summary}

Grounding knowledge sources:
{grounding_context}

Instructions:

• Provide compassionate, calm support.
• Help the patient tolerate uncertainty rather than eliminate it.
• Encourage ERP-consistent responses when relevant.
• Avoid sounding clinical or robotic.
• Speak naturally like a supportive coach.

The response should be:
• supportive
• grounded in therapy principles
• not overly long
• not giving reassurance.

Write the final response to the patient.
"""


def _format_chat_history(history: List[Dict[str, str]]) -> str:

    if not history:
        return "No recent history."

    lines: List[str] = []

    for msg in history[-6:]:
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "").strip()

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)