# app/education/fear_ladder/config.py
from __future__ import annotations
import os

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")

KB_TOP_K = int(os.getenv("EDU_KB_TOP_K", "8"))

# Web fallback toggle
USE_WEB_FALLBACK = os.getenv("EDU_USE_WEB_FALLBACK", "true").lower() == "true"

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Extra guardrail: even if someone tries to call web node manually, we keep it restricted
ALLOWED_DOMAINS = [
    "iocdf.org",
    "nimh.nih.gov",
    "nhs.uk",
    "mayoclinic.org",
    "my.clevelandclinic.org",
    "apa.org",
]