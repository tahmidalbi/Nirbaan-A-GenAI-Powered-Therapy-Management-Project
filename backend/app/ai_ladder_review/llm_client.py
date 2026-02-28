# app/ai_ladder_review/llm_client.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")


class LLMClient:
    """
    Minimal OpenAI wrapper that returns parsed JSON dict.
    Mirrors your IntakeSummarizerAgent style.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def call_json(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        last_err: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=temperature,
                    messages=messages,
                )
                raw = resp.choices[0].message.content or ""
                data = self._safe_json_load(raw)
                return data
            except Exception as e:
                last_err = e

        raise RuntimeError(f"LLM call failed after retries: {last_err}") from last_err

    def _safe_json_load(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()

        # If model returns extra text, try to extract first JSON object
        if not text.startswith("{"):
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last != -1 and last > first:
                text = text[first : last + 1]

        try:
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError("Top-level JSON is not an object")
            return obj
        except Exception as e:
            raise ValueError(f"Invalid JSON from LLM: {e}") from e