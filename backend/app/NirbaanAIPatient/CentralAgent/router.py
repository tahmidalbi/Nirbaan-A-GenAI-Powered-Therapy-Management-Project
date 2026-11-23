import logging
import os
from typing import Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.verifier import (
    ESCALATION_LLM_MAX_RETRIES,
    ESCALATION_LLM_TIMEOUT_SECONDS,
    explicit_escalation_reason,
)

log = logging.getLogger(__name__)


class RouterOutput(BaseModel):
    route: str


def router_node(state: Dict):

    # Clear crisis wording or an explicit request for a person goes straight to
    # human escalation, using the same fixed rules as the verifier, so the LLM
    # router cannot send it to psychoeducation or web search.
    if explicit_escalation_reason(state.get("user_message", "") or ""):
        return {"route": "human_escalation"}

    prompt = f"""
You are routing a patient message to the correct AI agent.

Agents available:

psychoeducation
- questions about OCD
- asking how ERP works
- learning concepts

support
- emotional distress
- discouragement
- ERP burnout
- reassurance seeking
- rough day

human_escalation
- patient explicitly asks for a human helper
- patient says they need someone to come in person
- patient asks for emergency personnel / human assistance
- patient is in crisis and requests real-world intervention

Patient message:
{state["user_message"]}

Return route.
"""

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-2026-03-05"),
            timeout=ESCALATION_LLM_TIMEOUT_SECONDS,
            max_retries=ESCALATION_LLM_MAX_RETRIES,
        ).with_structured_output(RouterOutput)
        result = llm.invoke(prompt)
    except Exception as exc:
        # Router unavailable is not a crisis: send the message to the escalation
        # verifier, which decides (and escalates by default if it is also unavailable).
        log.warning("Router LLM unavailable (%s); sending message to escalation check", type(exc).__name__)
        return {"route": "human_escalation", "router_unavailable": True}

    route = result.route

    if route not in ["psychoeducation", "support", "human_escalation"]:
        route = "support"

    return {"route": route}