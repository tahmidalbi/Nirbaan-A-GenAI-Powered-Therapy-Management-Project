import os
from typing import Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class RouterOutput(BaseModel):
    route: str


def router_node(state: Dict):

    llm = ChatOpenAI(
        model=("gpt-5.3-chat-latest"),
        
    ).with_structured_output(RouterOutput)

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

    result = llm.invoke(prompt)

    route = result.route

    if route not in ["psychoeducation", "support", "human_escalation"]:
        route = "support"

    return {"route": route}