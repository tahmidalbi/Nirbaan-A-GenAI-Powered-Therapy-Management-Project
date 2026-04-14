from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI


DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-5.3")


class IntakeSummarizerAgent:
    """
    OCD-focused intake summarizer.
    - Produces therapist-facing bullets
    - Produces structured snapshot for downstream agents
    - Does NOT infer or diagnose beyond user-provided info
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def _normalize_input(self, intake: Dict[str, Any]) -> Dict[str, Any]:
        # Keep only the fields we want the model to see.
        return {
            "your_story": intake.get("your_story", "") or "",
            "when_started": intake.get("when_started", "") or "",
            "tried_previous_therapy": bool(intake.get("tried_previous_therapy", False)),
            "previous_therapy_details": intake.get("previous_therapy_details"),
            "taken_medication": bool(intake.get("taken_medication", False)),
            "medication_details": intake.get("medication_details"),
            "affected_life_areas": intake.get("affected_life_areas"),
            "other_conditions": intake.get("other_conditions"),
            "issues": intake.get("issues") or [],
        }

    def summarize(self, intake_dict: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Returns:
            (summary_text_bullets, structured_snapshot_dict)
        """
        payload = self._normalize_input(intake_dict)

        system = (
            "You are a clinical intake summarizer for an OCD-focused therapy app. "
            "You must be faithful to the patient text and must NOT invent facts. "
            "If something is not provided, write 'Unknown' or null. "
            "Do NOT claim a diagnosis unless the patient explicitly states it. "
            "Extract OCD-relevant signals ONLY if present (obsessions, compulsions, avoidance, triggers, reassurance-seeking). "
            "Output STRICT JSON only."
        )

        user = {
            "task": "Summarize this intake for a therapist and for downstream clinical agents.",
            "intake": payload,
            "required_output_json_schema": {
                "summary_bullets": "list of 8-12 short bullets",
                "structured_snapshot": {
                    "presenting_story_one_liner": "string",
                    "timeline": {"when_started": "string", "course_or_pattern": "string or Unknown"},
                    "issues_sorted": "list of {issue, severity}",
                    "life_impact": "string or Unknown",
                    "avoidance_behaviors": "list of strings (only if present) else []",
                    "ocd_signals": {
                        "obsessions": "list of strings (only if present) else []",
                        "compulsions": "list of strings (only if present) else []",
                        "reassurance_seeking": "string or Unknown",
                        "triggers": "list of strings (only if present) else []",
                    },
                    "past_treatment": {
                        "therapy_tried": "bool",
                        "therapy_details": "string or Unknown",
                        "medication_taken": "bool",
                        "medication_details": "string or Unknown",
                    },
                    "other_conditions": "string or Unknown",
                    "missing_info": "list of strings (key missing items)",
                    "evidence_snippets": "optional list of {claim, evidence_quote} with short quotes (<=20 words each)"
                }
            }
        }

        # Ask for JSON. We'll parse and validate lightly.
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )

        raw = resp.choices[0].message.content or "{}"

        # Robust JSON parse (handles accidental surrounding text)
        data = self._safe_json_load(raw)

        summary_bullets = data.get("summary_bullets") or []
        structured = data.get("structured_snapshot") or {}

        # Convert bullets list -> text block for UI
        summary_text = self._bullets_to_text(summary_bullets)

        # Ensure issues_sorted exists and is sorted (as a backup)
        structured = self._postprocess_structured(structured, payload)

        return summary_text, structured

    def _safe_json_load(self, text: str) -> Dict[str, Any]:
        text = text.strip()

        # If model returns extra text, try to extract the first JSON object.
        if not text.startswith("{"):
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last != -1 and last > first:
                text = text[first:last + 1]

        try:
            return json.loads(text)
        except Exception:
            # Absolute fallback: return minimal safe output
            return {
                "summary_bullets": ["AI summary failed to parse. Please view raw intake."],
                "structured_snapshot": {"missing_info": ["AI parse failure - summary unavailable."]}
            }

    def _bullets_to_text(self, bullets: List[Any]) -> str:
        clean = []
        for b in bullets:
            if isinstance(b, str) and b.strip():
                clean.append(f"- {b.strip()}")
        if not clean:
            return "- Summary not available."
        return "\n".join(clean)

    def _postprocess_structured(self, structured: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure issues_sorted exists
        issues = payload.get("issues") or []
        try:
            issues_sorted = sorted(
                [{"issue": i.get("issue", ""), "severity": int(i.get("severity", 0))} for i in issues],
                key=lambda x: x["severity"],
                reverse=True,
            )
        except Exception:
            issues_sorted = []

        structured.setdefault("issues_sorted", issues_sorted)

        # Normalize Unknown fields
        def norm_unknown(v: Any) -> Any:
            if v is None:
                return "Unknown"
            if isinstance(v, str) and not v.strip():
                return "Unknown"
            return v

        structured.setdefault("timeline", {})
        structured["timeline"]["when_started"] = norm_unknown(structured["timeline"].get("when_started", payload.get("when_started")))
        structured["timeline"]["course_or_pattern"] = norm_unknown(structured["timeline"].get("course_or_pattern"))

        structured["life_impact"] = norm_unknown(structured.get("life_impact", payload.get("affected_life_areas")))
        structured["other_conditions"] = norm_unknown(structured.get("other_conditions", payload.get("other_conditions")))

        structured.setdefault("ocd_signals", {})
        for k in ["obsessions", "compulsions", "triggers"]:
            structured["ocd_signals"].setdefault(k, [])
            if structured["ocd_signals"][k] is None:
                structured["ocd_signals"][k] = []
        structured["ocd_signals"]["reassurance_seeking"] = norm_unknown(structured["ocd_signals"].get("reassurance_seeking"))

        structured.setdefault("avoidance_behaviors", [])
        if structured["avoidance_behaviors"] is None:
            structured["avoidance_behaviors"] = []

        structured.setdefault("past_treatment", {})
        structured["past_treatment"]["therapy_tried"] = bool(payload.get("tried_previous_therapy", False))
        structured["past_treatment"]["therapy_details"] = norm_unknown(payload.get("previous_therapy_details")) if payload.get("tried_previous_therapy") else "Unknown"
        structured["past_treatment"]["medication_taken"] = bool(payload.get("taken_medication", False))
        structured["past_treatment"]["medication_details"] = norm_unknown(payload.get("medication_details")) if payload.get("taken_medication") else "Unknown"

        structured.setdefault("missing_info", [])
        if structured["missing_info"] is None:
            structured["missing_info"] = []

        # OCD context: recommend missing items that matter for ERP if not provided
        # (as "missing_info" suggestions, not assumptions)
        suggested_missing = []
        if not structured["ocd_signals"].get("obsessions"):
            suggested_missing.append("Obsessions not clearly described (intrusive thoughts/images/urges).")
        if not structured["ocd_signals"].get("compulsions"):
            suggested_missing.append("Compulsions not clearly described (checking, washing, mental rituals, reassurance-seeking).")
        if not structured.get("avoidance_behaviors"):
            suggested_missing.append("Avoidance behaviors not clearly described.")
        # You currently don't collect goals/safety; so they should always appear as missing unless your intake adds them
        suggested_missing.append("Treatment goals not provided.")
        suggested_missing.append("Safety screening not provided (self-harm / harm-to-others thoughts).")

        # Merge unique
        existing = set([str(x) for x in structured["missing_info"] if x])
        for s in suggested_missing:
            if s not in existing:
                structured["missing_info"].append(s)

        return structured
