# app/education/ocd_core/llm.py
from __future__ import annotations
from langchain_openai import ChatOpenAI
from app.education.ocd_core.config import LLM_MODEL


def get_llm():
    return ChatOpenAI(model=LLM_MODEL, temperature=0)
