from __future__ import annotations

from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


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
    Strict verifier node:
    - Human handover is triggered only for intense distress / immediate inability to cope /
      need for real-world intervention.
    - Asking for help alone is NOT enough.
    - Harm OCD / self-harm OCD intrusive thoughts should NOT be treated as genuine self-harm risk
      unless there are explicit indicators of real intent, plan, or immediate danger.
    """

    user_message = state.get("user_message", "") or ""
    chat_history = state.get("recent_chat_history", []) or []
    patient_conditions = state.get("patient_conditions", "") or ""

    history_text = _format_history(chat_history)

    llm = ChatOpenAI(
        model="gpt-5.3-chat-latest",
      
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