# app/education/fear_ladder/llm.py
from __future__ import annotations
from langchain_openai import ChatOpenAI
from app.education.fear_ladder.config import LLM_MODEL

def get_llm():
    # temperature 0 for stable JSON
    return ChatOpenAI(model=LLM_MODEL, temperature=0)