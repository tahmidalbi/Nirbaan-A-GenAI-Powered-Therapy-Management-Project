from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# Explicit requests for a person and clear crisis wording always escalate, without the LLM.
# Ambiguous OCD-style content (e.g. "what if I hurt someone?") is left to the LLM verifier.
_HUMAN_REQUEST_PATTERNS = [
    r"\b(real|actual)\s+(person|human|helper|people)\b",
    r"\bhuman\s+(help|helper|support)\b",
    r"\b(talk|speak)\s+(to|with)\s+(a\s+)?(human|person|real person)\b",
    r"\bneed\s+a\s+(human|person)\b",
    r"\bnot\s+(a\s+)?(chatbot|bot|ai)\b",
    r"\bescalate\b",
    r"\b(send|get|bring)\s+(me\s+)?(someone|somebody|a\s+(human|person|helper)|help)\b",
    r"\b(contact|alert|notify|connect|call)\b[^.?!]*\b(care\s+team|support\s+team|support\s+people|emergency|human|helper)\b",
    r"\b(someone|somebody|a\s+person)\b[^.?!]*\b(come|be\s+here|check\s+on\s+me|call\s+me|see\s+me)\b",
]
_CRISIS_PATTERNS = [
    r"\b(i'?m|i\s+am)\s+in\s+(a\s+)?crisis\b",
    r"\bemergency\b",
    r"\b(not|don'?t\s+feel|do\s+not\s+feel)\s+safe\b",
    r"\bsuicid",
    r"\bkill\s+myself\b",
    r"\bend\s+my\s+life\b",
    r"\bwant\s+to\s+die\b",
]


def explicit_escalation_reason(message: str) -> Optional[str]:
    text = message.lower().replace("’", "'")
    if any(re.search(p, text) for p in _CRISIS_PATTERNS):
        return "clear crisis wording"
    if any(re.search(p, text) for p in _HUMAN_REQUEST_PATTERNS):
        return "explicit request for a human or emergency help"
    return None


class VerifierOutput(BaseModel):
    needs_human_help: bool = Field(
        ...,
        description="True only when immediate human handover is necessary."
    )
    reasoning: str = Field(
        ...,
        description="Brief clinical-style explanation focused on distress level, immediacy, and whether AI can continue."
    )


def _format_history(chat_history: List[Dict[str, str]]) -> str:
    history_text = ""
    for turn in chat_history[-6:]:
        role = turn.get("role", "")
        content = turn.get("content", "")
        role_label = "Patient" if role == "user" else "AI Assistant"
        history_text += f"{role_label}: {content}\n"
    return history_text.strip()


def verifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifier node:
    - Explicit requests for a human and clear crisis wording escalate by rule.
    - Everything else goes to a strict LLM check: escalate only for intense distress,
      immediate inability to cope, or need for real-world intervention.
    - Harm OCD / self-harm OCD intrusive thoughts should NOT be treated as genuine self-harm risk
      unless there are explicit indicators of real intent, plan, or immediate danger.
    """

    user_message = state.get("user_message", "") or ""

    reason = explicit_escalation_reason(user_message)
    if reason:
        return {
            "needs_human_help": True,
            "verifier_reasoning": f"Escalated by rule: {reason}.",
        }

    chat_history = state.get("recent_chat_history", []) or []
    patient_conditions = state.get("patient_conditions", "") or ""

    history_text = _format_history(chat_history)

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-2026-03-05"),
      
    ).with_structured_output(VerifierOutput)

    prompt = f"""
You are a STRICT clinical triage verifier for an OCD/ERP support system.

Your task is NOT to escalate just because the patient asks for human help.
Your task is to decide whether the AI can continue safely and adequately,
or whether immediate human handover is necessary.

CORE RULE:
Set needs_human_help = true ONLY if there is evidence of INTENSE DISTRESS,
IMMEDIATE INABILITY TO COPE, or NEED FOR REAL-WORLD HUMAN INTERVENTION.

Set needs_human_help = false in all other cases.

--------------------------------
ESCALATE TO HUMAN HELP = TRUE ONLY WHEN:
--------------------------------
1. The patient is in intense, acute distress that the AI cannot reasonably contain through conversation.
2. The patient appears unable to regulate or continue safely in the current moment.
3. The situation requires real-world human presence or practical intervention now.
4. There are clear signs of imminent danger, loss of control in the immediate moment,
   or urgent functional breakdown that AI support cannot manage alone.

--------------------------------
DO NOT ESCALATE = FALSE WHEN:
--------------------------------
1. The patient merely asks for "human help" or says they want a person.
2. The patient is distressed but still conversational, coherent, and manageable by AI support.
3. The patient is venting, reassurance-seeking, confused, overwhelmed, or upset,
   but there is no sign of immediate inability to cope.
4. The patient describes intrusive OCD thoughts, including harm OCD or self-harm OCD themes,
   without evidence of genuine intent or immediate danger.
5. The patient says things like:
   - "I'm afraid I might harm myself"
   - "I'm developing an obsession around self-harm"
   - "What if I lose control?"
   when the pattern is obsessional fear / intrusive thought / ego-dystonic OCD content.

--------------------------------
IMPORTANT OCD-SPECIFIC RULE:
--------------------------------
If the content is consistent with OCD intrusive thoughts, obsessional doubt, or fear of self-harm,
DO NOT classify that alone as actual self-harm risk.

Examples that should usually remain FALSE:
- "I'm scared I'm developing a self-harm obsession."
- "What if I hurt myself?"
- "I don't want to do it, I'm terrified of the thought."
- "This thought is stuck in my head and I want help because it scares me."

These are OCD-style fear statements unless there is clear evidence of real intent,
a real wish to act, immediate danger, or inability to remain safe.

--------------------------------
PRIORITIZE THESE SIGNALS:
--------------------------------
A. Distress intensity right now
B. Ability to continue engaging with AI support
C. Whether immediate human presence is actually necessary
D. Whether the message reflects intrusive OCD fear rather than real intent

--------------------------------
OUTPUT STYLE:
--------------------------------
- Be strict and conservative about escalation.
- Do not escalate from keywords alone.
- Do not escalate from "human help" language alone.
- Only escalate for intense distress / immediate danger / real-world intervention need.
- Keep reasoning brief and specific.

Patient conditions:
{patient_conditions}

Recent conversation:
{history_text}

Patient's latest message:
{user_message}

Return:
1. needs_human_help
2. reasoning
""".strip()

    result = llm.invoke(prompt)

    return {
        "needs_human_help": result.needs_human_help,
        "verifier_reasoning": result.reasoning,
    }