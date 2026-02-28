# app/education/ocd_core/web.py
from __future__ import annotations
from typing import Any, Dict, List

from app.education.ocd_core.config import ALLOWED_DOMAINS, TAVILY_API_KEY


def tavily_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Web fallback. Only called when KB is insufficient."""
    if not TAVILY_API_KEY:
        return []

    from langchain_community.tools.tavily_search import TavilySearchResults

    tool = TavilySearchResults(
        max_results=k,
        include_answer=False,
        include_raw_content=True,
        include_domains=ALLOWED_DOMAINS,
        tavily_api_key=TAVILY_API_KEY,
    )

    result = tool.invoke({"query": query})
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "results" in result:
        return result["results"] or []
    return []
