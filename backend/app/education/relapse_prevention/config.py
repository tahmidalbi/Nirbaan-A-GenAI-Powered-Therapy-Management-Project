# app/education/relapse_prevention/config.py
from __future__ import annotations
import os

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")

KB_TOP_K = int(os.getenv("EDU_RP_KB_TOP_K", "8"))

USE_WEB_FALLBACK = os.getenv("EDU_RP_USE_WEB_FALLBACK", "true").lower() == "true"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

ALLOWED_DOMAINS = [
    "iocdf.org",
    "nimh.nih.gov",
    "nhs.uk",
    "mayoclinic.org",
    "my.clevelandclinic.org",
    "apa.org",
]
