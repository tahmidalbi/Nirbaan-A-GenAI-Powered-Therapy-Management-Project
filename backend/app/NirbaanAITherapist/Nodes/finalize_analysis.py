from __future__ import annotations

from typing import Any, Dict

from app.NirbaanAITherapist.state import NirbaanAITherapistState


def finalize_analysis_node(state: NirbaanAITherapistState) -> Dict[str, Any]:
    """
    Finalize therapist-side analysis output.

    Produces:
    - final_analysis: final therapist-facing analysis content
    - final_response: chat-ready assistant response
    - status: completed
    """

    analysis_summary = (state.get("analysis_summary") or "").strip()
    draft_analysis = (state.get("draft_analysis") or "").strip()

    final_analysis = analysis_summary or draft_analysis or "No analysis could be generated."

    final_response = _build_final_response(final_analysis)

    return {
        "final_analysis": final_analysis,
        "final_response": final_response,
        "status": "completed",
    }


def _build_final_response(final_analysis: str) -> str:
    """
    Format the final analysis for insertion into therapist chat.
    """
    return final_analysis.strip()