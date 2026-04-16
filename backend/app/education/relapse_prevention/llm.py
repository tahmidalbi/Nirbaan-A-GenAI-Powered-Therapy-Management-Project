# app/education/relapse_prevention/llm.py
from __future__ import annotations
from langchain_openai import ChatOpenAI
from app.education.relapse_prevention.config import LLM_MODEL


def get_llm():
    return ChatOpenAI(model=LLM_MODEL)
