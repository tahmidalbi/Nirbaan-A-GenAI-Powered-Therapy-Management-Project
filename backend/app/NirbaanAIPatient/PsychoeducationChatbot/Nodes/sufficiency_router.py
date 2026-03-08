from __future__ import annotations

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


def sufficiency_router(state: PsychoeducationState) -> str:
    """
    Route after sufficiency checking.

    Returns one of:
    - "generate"
    - "refine_query"
    - "web_search"
    """
    retrieval_sufficient = bool(state.get("retrieval_sufficient", False))
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 2))

    if retrieval_sufficient:
        return "generate"

    if retry_count < max_retries:
        return "refine_query"

    return "web_search"