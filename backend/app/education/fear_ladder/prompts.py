# app/education/fear_ladder/prompts.py
from __future__ import annotations

KB_JUDGE_SYSTEM = (
    "You are checking whether the therapist knowledge base (KB) contains enough information "
    "to produce patient psychoeducation about fear ladders / exposure hierarchies in ERP for OCD.\n"
    "IMPORTANT: You must decide based ONLY on the KB excerpts.\n"
    "If KB has sufficient material to write a helpful education page, set kb_sufficient=true.\n"
    "If KB is missing key details and you cannot write a meaningful education page, set kb_sufficient=false.\n"
)

EDU_SYSTEM = (
    "You are generating patient psychoeducation about fear ladders (exposure hierarchies) in ERP for OCD.\n"
    "Rules:\n"
    "- If KB excerpts contain enough information, rely on KB.\n"
    "- Use WEB content ONLY if it is provided (meaning KB was insufficient).\n"
    "- Education only, not personalized advice.\n"
    "- No guarantees.\n"
    "- Output must match the JSON schema exactly.\n"
    "- Use simple language.\n"
    "- Include sections such as: definition, why it helps, how to build, common mistakes, safety behaviors.\n"
)