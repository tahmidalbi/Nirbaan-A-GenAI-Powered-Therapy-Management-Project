# ai_ladder_review_v2/ladder_review_agent/prompts/symptom_finder_prompt.py
from __future__ import annotations


def build_symptom_finder_prompt(
    taxonomy_context_text: str,
    intake_text: str,
    batch_text: str,
    recheck_mode: bool = False,
) -> str:
    """
    Extracts OCD-structured patterns from intake + a single log batch.
    Requires evidence quotes.
    Output must be strict JSON.
    """
    recheck_line = ""
    if recheck_mode:
        recheck_line = (
            "RECHECK MODE:\n"
            "- Do a second pass focusing on subtle patterns that are easy to miss.\n"
            "- Pay special attention to mental rituals, rumination, attention monitoring (somatic/sensorimotor), reassurance seeking, and avoidance.\n"
        )

    return f"""
You are an information extraction system for therapist review of OCD patterns.

You MUST follow these constraints:
- Evidence required: every extracted item MUST include at least 1 verbatim quote from the provided intake or logs.
- If you cannot cite a verbatim quote, do NOT output that item.
- Do NOT over-flag normal life stressors (grief, sleep issues, exams, workload) as OCD unless an OCD loop is evident: intrusion/discomfort + repetitive neutralizing/avoidance/reassurance/checking.
- Taxonomy is guidance, not a whitelist: you MAY extract patterns not explicitly named in the taxonomy if the OCD loop is present and evidence exists.

{recheck_line}

TAXONOMY CONTEXT (retrieved):
{taxonomy_context_text}

PATIENT INTAKE (raw or summarized):
{intake_text}

CURRENT LOG BATCH:
{batch_text}

TASK:
Extract OCD-structured patterns that may represent an obsession-compulsion loop.

For each pattern, output:
- id: unique stable id like "C1", "C2"...
- obsession: feared meaning / doubt / intrusive content / or not-just-right discomfort
- compulsions: list of compulsions (behavioral or mental). If unclear, use an empty list.
- evidence: list of evidence objects with exact quotes (verbatim) and where they came from
- label: short human-readable label that therapist can scan (e.g., "Somatic hyperawareness of blinking", "Rumination about responsibility")

IMPORTANT:
- Do NOT include advice or reassurance.
- Keep obsession/compulsion phrasing close to the patient's language.
- If you only have a trigger and no compulsion evidence, you may output it as "potential_pattern": true (still must include evidence quote).
- If compulsion is unknown and patient wrote "don't know", consider potential patterns ONLY if the text suggests repetitive monitoring/neutralizing/avoidance/reassurance.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "candidates": [
    {{
      "id": "C1",
      "label": "string",
      "obsession": "string",
      "compulsions": ["string"],
      "potential_pattern": false,
      "evidence": [
        {{
          "source_type": "intake" | "daily_log",
          "source_id": "string",
          "source_date": "YYYY-MM-DD",
          "field_name": "string",
          "quote_text": "verbatim snippet"
        }}
      ]
    }}
  ]
}}

RULES:
- Output ONLY valid JSON.
- No markdown, no commentary.
""".strip()