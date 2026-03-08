from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.NirbaanAIPatient.GeneralSupportChatbot.state import GeneralSupportState


class SufficiencyOutput(BaseModel):
    retrieval_sufficient: bool = Field(
        ...,
        description="Whether the therapist KB contains enough information to support the response."
    )
    insufficiency_reason: str = Field(
        default="",
        description="Short explanation why KB is insufficient."
    )


def sufficiency_checker_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Decide whether retrieved KB chunks are enough to answer the patient.

    If not enough → graph will route to web_search.
    """

    user_message = (state.get("user_message") or "").strip()
    support_type = (state.get("support_type") or "other").strip()
    support_goal = (state.get("support_goal") or "").strip()

    kb_chunks = state.get("kb_chunks") or []
    kb_context_summary = (state.get("kb_context_summary") or "").strip()

    if not kb_chunks:
        return {
            "retrieval_sufficient": False,
            "insufficiency_reason": "No knowledge base chunks were retrieved."
        }

    llm = _get_llm()
    structured_llm = llm.with_structured_output(SufficiencyOutput)

    prompt = _build_prompt(
        user_message=user_message,
        support_type=support_type,
        support_goal=support_goal,
        kb_context_summary=kb_context_summary,
    )

    result: SufficiencyOutput = structured_llm.invoke(prompt)

    return {
        "retrieval_sufficient": result.retrieval_sufficient,
        "insufficiency_reason": (result.insufficiency_reason or "").strip(),
    }


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2"),
        temperature=0,
    )


def _build_prompt(
    *,
    user_message: str,
    support_type: str,
    support_goal: str,
    kb_context_summary: str,
) -> str:
    return f"""
You are evaluating whether retrieved therapist knowledge base content
is sufficient to help respond to a patient's support message.

Your job is NOT to write the response.

Your job is ONLY to decide if the KB contains enough information.

Rules:

1. If the KB contains therapy guidance that can reasonably support the response,
   mark retrieval_sufficient = true.

2. If the KB does NOT contain relevant therapy guidance,
   mark retrieval_sufficient = false.

3. If the KB is only loosely related or incomplete,
   mark retrieval_sufficient = false.

4. Be conservative — if you are unsure, choose false so the system can use web fallback.

5. Do NOT invent missing information.

6. The decision should consider:
   - the patient's message
   - the support_type
   - the support_goal

Patient message:
{user_message}

Support type:
{support_type}

Support goal:
{support_goal}

Retrieved KB context:
{kb_context_summary}

Return structured output with:
- retrieval_sufficient
- insufficiency_reason
""".strip()