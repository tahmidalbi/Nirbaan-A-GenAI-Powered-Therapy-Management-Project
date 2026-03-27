from __future__ import annotations

import requests

from .config import settings


def generate_script_with_ollama(prompt_text: str) -> str:
    """Send the finalized prompt to the fine-tuned local SLM via Ollama and
    return the generated imaginal exposure script text."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt_text,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Ollama request failed ({settings.OLLAMA_BASE_URL}): {exc}"
        ) from exc

    data = response.json()
    script = data.get("response", "").strip()
    if not script:
        raise RuntimeError(
            f"Ollama returned an empty response for model '{settings.OLLAMA_MODEL}'"
        )
    return script