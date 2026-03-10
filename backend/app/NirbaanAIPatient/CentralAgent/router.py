import os
from typing import Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class RouterOutput(BaseModel):
    route: str


def router_node(state: Dict):

    llm = ChatOpenAI(
        model=("gpt-5-nano"),
        temperature=0,
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

Patient message:
{state["user_message"]}

Return route.
"""

    result = llm.invoke(prompt)

    route = result.route

    if route not in ["psychoeducation", "support"]:
        route = "support"

    return {"route": route}