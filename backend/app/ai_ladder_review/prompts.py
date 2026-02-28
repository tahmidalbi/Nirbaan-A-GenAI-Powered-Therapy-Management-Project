# app/ai_ladder_review/prompts.py
from __future__ import annotations

import json
from typing import Any, Dict, List

from app.ai_ladder_review.taxonomy import get_ocd_rulebook_text, OCD_TAXONOMY_VERSION


CALL1_SYSTEM = (
    "You are a clinical documentation assistant for an OCD-focused ERP app.\n"
    "Your job is to extract recurring fear→response patterns from provided intake and daily logs.\n\n"
    "HARD RULES:\n"
    "- Output MUST be valid JSON only. No markdown. No extra text.\n"
    "- You MUST follow the provided JSON schema exactly.\n"
    "- Every structure MUST include evidence quotes copied VERBATIM from the provided text.\n"
    "- Every structure MUST link at least one compulsion to one obsession.\n"
    "- Do NOT use diagnostic language (do not say the patient 'has OCD' or diagnose).\n"
    "- Do NOT mention or compare against the fear ladder in this step.\n"
    "- If evidence is insufficient, do not include the structure.\n"
    "- Prefer recurring/repeated patterns.\n"
)

CALL1_USER_TEMPLATE = """
You are given:
1) A FIXED OCD RULEBOOK (below)
2) Patient intake responses
3) Last 7 days of self-monitoring logs

Task:
Extract recurring “structures” consisting of:
- obsession (feared outcome / uncertainty-driven fear)
- linked compulsion(s) (behavior or mental act done to reduce anxiety/uncertainty)
- rationale (why this is a coherent obsession↔compulsion pattern, referencing repetition)
- evidence: verbatim quotes with provenance

Return JSON matching this schema:

{{
  "structures": [
    {{
      "id": "temp_1",
      "obsession": "string",
      "compulsions": ["string", "string"],
      "rationale": "string",
      "evidence": [
        {{
          "source_type": "intake" | "daily_log",
          "source_id": "string",
          "date": "YYYY-MM-DD" | null,
          "field_name": "string",
          "quote_text": "string"
        }}
      ]
    }}
  ]
}}

ID rules:
- Use ids temp_1, temp_2, temp_3... in order.
- Do not skip numbers.

Evidence rules:
- Each structure MUST include at least 2 evidence items.
- Evidence must be VERBATIM quotes copied from the provided intake/log text.
- Evidence must include at least one daily_log quote when logs exist.
- quote_text must be short (max ~280 chars each). Prefer the most revealing sentence.

Structure rules:
- Obsession = intrusive fear / doubt / “what if” / feared consequence (uncertainty-driven).
- Compulsion = action/mental act/avoidance/reassurance-seeking/checking/reviewing meant to reduce fear or prevent the feared outcome.
- Link: compulsions must clearly be performed BECAUSE of the obsession.
- Exclude: general stress, depression rumination, purely realistic planning, habits without fear reduction.
- Include mental compulsions when clear (reviewing, praying “just right”, neutralizing, repeating phrases, analyzing memories).
- If it could be either compulsion or normal coping, only include if the text clearly shows it is driven by fear/uncertainty reduction.

No diagnosis language. Use neutral phrasing like “fear + behavior pattern”.

FIXED OCD RULEBOOK (version {taxonomy_version}):
{rulebook}

Now analyze the data below.

INPUT JSON:
{input_json}
""".strip()


CALL2_SYSTEM = (
    "You are a strict JSON matching engine.\n"
    "HARD RULES:\n"
    "- Output MUST be valid JSON only. No markdown. No extra text.\n"
    "- You MUST ONLY select from the provided structure IDs.\n"
    "- Do NOT invent new IDs or new structures.\n"
    "- Be conservative: if a ladder item clearly covers the same fear/compulsion pattern, it is NOT missing.\n"
)

CALL2_USER_TEMPLATE = """
You are given:
1) Extracted structures (with IDs, obsessions, compulsions)
2) Fear ladder items text (what the patient already included)

Task:
Return ONLY the IDs of structures that are NOT represented in the ladder.

Definition of “represented”:
A structure is represented if ANY ladder item semantically covers:
- the same feared outcome (obsession meaning), AND
- at least one linked compulsion/response pattern (or the same avoidance/reassurance/checking/mental reviewing theme)

Do NOT over-flag subtypes.
If the ladder already has “fear of contamination + washing/checking”, do not flag a structure that is merely a slightly different contamination example.

Output JSON schema:
{{
  "missing_ids": ["temp_2", "temp_4"]
}}

Rules:
- missing_ids must be a subset of provided IDs.
- If none are missing, return {{"missing_ids": []}}.

STRUCTURES_JSON:
{structures_json}

LADDER_ITEMS_TEXT:
{ladder_text}
""".strip()


def build_call1_messages(input_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    rulebook = get_ocd_rulebook_text()
    user_text = CALL1_USER_TEMPLATE.format(
        taxonomy_version=OCD_TAXONOMY_VERSION,
        rulebook=rulebook,
        input_json=json.dumps(input_payload, ensure_ascii=False),
    )
    return [
        {"role": "system", "content": CALL1_SYSTEM},
        {"role": "user", "content": user_text},
    ]


def build_call2_messages(structures_json: Dict[str, Any], ladder_text: str) -> List[Dict[str, str]]:
    user_text = CALL2_USER_TEMPLATE.format(
        structures_json=json.dumps(structures_json, ensure_ascii=False),
        ladder_text=ladder_text or "",
    )
    return [
        {"role": "system", "content": CALL2_SYSTEM},
        {"role": "user", "content": user_text},
    ]