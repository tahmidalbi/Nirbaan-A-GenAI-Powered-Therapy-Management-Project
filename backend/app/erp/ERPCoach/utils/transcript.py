# app/erp/ERPCoach/utils/transcript.py
from __future__ import annotations

from typing import Iterable, List, Literal, Optional, Sequence

from app.erp.models import ERPChatMessage


Role = Literal["patient", "coach", "system"]


def normalize_role(role: str) -> Role:
    """
    Normalize arbitrary role strings into one of:
      - patient
      - coach
      - system
    """
    r = (role or "").strip().lower()
    if r in ("user", "patient", "human"):
        return "patient"
    if r in ("assistant", "ai", "coach", "bot"):
        return "coach"
    return "system"


def format_transcript_lines(
    messages: Sequence[ERPChatMessage],
    *,
    max_messages: int = 20,
    max_chars_per_message: int = 1200,
) -> List[str]:
    """
    Formats the last N messages into compact readable lines for LLM prompting.

    Output style:
      PATIENT: ...
      COACH: ...
      SYSTEM: ...

    Truncates long messages to avoid huge prompts.
    """
    if not messages:
        return []

    # Keep only last max_messages (assuming messages already chronological)
    trimmed = messages[-max_messages:]

    lines: List[str] = []
    for m in trimmed:
        role = normalize_role(getattr(m, "role", "system"))
        text = (getattr(m, "content", "") or "").strip()

        if len(text) > max_chars_per_message:
            text = text[: max_chars_per_message].rstrip() + "…"

        prefix = "PATIENT" if role == "patient" else "COACH" if role == "coach" else "SYSTEM"
        lines.append(f"{prefix}: {text}")

    return lines


def format_transcript_block(
    messages: Sequence[ERPChatMessage],
    *,
    max_messages: int = 20,
    max_chars_per_message: int = 1200,
) -> str:
    """
    Returns a single string block of the transcript lines joined by newline.
    """
    lines = format_transcript_lines(
        messages,
        max_messages=max_messages,
        max_chars_per_message=max_chars_per_message,
    )
    return "\n".join(lines)


def extract_last_patient_message(messages: Sequence[ERPChatMessage]) -> Optional[str]:
    """
    Returns the most recent patient message content from the message list, or None.
    """
    for m in reversed(messages):
        if normalize_role(getattr(m, "role", "")) == "patient":
            return (getattr(m, "content", "") or "").strip() or None
    return None