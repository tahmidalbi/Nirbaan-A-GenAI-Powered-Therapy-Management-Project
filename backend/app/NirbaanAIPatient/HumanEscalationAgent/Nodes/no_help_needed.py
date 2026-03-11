from __future__ import annotations

from typing import Any, Dict


def no_help_needed_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Terminal node when the verifier decides human help is not needed.
    Returns a reassuring message encouraging the patient to continue
    talking with the AI assistant.
    """

    return {
        "final_response": (
            "I understand you're going through a tough time, and I'm here for you. "
            "Based on what you've shared, I believe we can continue working through this together. "
            "Please keep talking to me — I'm here to listen and support you. "
            "If at any point you feel you truly need someone in person, just let me know again."
        ),
    }
