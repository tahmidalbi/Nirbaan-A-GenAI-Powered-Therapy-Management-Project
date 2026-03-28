from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import settings
from .prompts import PROMPT_BUILDER_SYSTEM, REVISION_INTERPRETER_SYSTEM, BASE_INSTRUCTION


def get_llm():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing")
    return ChatOpenAI(
        model="gpt-5.2",
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1,
    )


def build_initial_prompt(
    *,
    obsession: str,
    compulsion: str,
    feared_consequence: str,
    script_intensity: str,
    subtype: str | None,
) -> str:
    llm = get_llm()

    user = f"""Create the exact final prompt text for the generator model.

Fixed instruction:
{BASE_INSTRUCTION}

Locked fields:
Obsession: {obsession}
Compulsion: {compulsion}
Feared consequence: {feared_consequence}
Script intensity: {script_intensity}
Exposure type: imaginal
Type: {subtype or ""}

Return only the final prompt text.
"""

    llm = get_llm()
    msg = llm.invoke([
        SystemMessage(content=PROMPT_BUILDER_SYSTEM),
        HumanMessage(content=user),
    ])
    return msg.content.strip()


def build_revised_prompt(
    *,
    obsession: str,
    compulsion: str,
    feared_consequence: str,
    script_intensity: str,
    subtype: str | None,
    therapist_feedback: str,
    previous_prompt: str,
    previous_script: str,
) -> str:
    llm = get_llm()

    user = f"""Revise the final generator prompt based on therapist feedback.

Locked fields:
Obsession: {obsession}
Compulsion: {compulsion}
Feared consequence: {feared_consequence}
Script intensity: {script_intensity}
Exposure type: imaginal
Type: {subtype or ""}

Previous prompt:
{previous_prompt}

Previous generated script:
{previous_script}

Therapist feedback:
{therapist_feedback}

Return only the revised final prompt text.
"""

    msg = llm.invoke([
        SystemMessage(content=REVISION_INTERPRETER_SYSTEM),
        HumanMessage(content=user),
    ])
    return msg.content.strip()