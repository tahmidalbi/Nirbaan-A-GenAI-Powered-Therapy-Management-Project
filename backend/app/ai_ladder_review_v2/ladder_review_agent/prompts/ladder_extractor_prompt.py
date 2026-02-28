# ai_ladder_review_v2/ladder_review_agent/prompts/ladder_extractor_prompt.py
from __future__ import annotations


def build_ladder_extractor_prompt(ladder_raw_text: str) -> str:
    """
    Normalizes patient-written ladder items into structured obsession/compulsion themes.
    Output must be strict JSON (no markdown).
    """
    return f"""
You are helping a therapist review a patient's OCD fear ladder.

TASK:
Normalize the patient's ladder items into a structured list of themes.
Each theme must include BOTH:
- obsession (feared meaning / intrusive doubt / "not-just-right" discomfort)
- compulsion(s) (behavioral OR mental OR reassurance OR avoidance OR safety behavior)

IMPORTANT:
- Use ONLY the provided ladder text. Do not invent items.
- If a ladder item is vague, keep it vague and do not guess missing details.
- Do not provide therapy advice. Only extract and normalize.

LADDER TEXT:
{ladder_raw_text}

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "ladder_items": [
    {{
      "id": "L1",
      "obsession": "string",
      "compulsions": ["string", "string"]
    }}
  ]
}}

RULES:
- Output ONLY valid JSON.
- No markdown, no commentary.
""".strip()