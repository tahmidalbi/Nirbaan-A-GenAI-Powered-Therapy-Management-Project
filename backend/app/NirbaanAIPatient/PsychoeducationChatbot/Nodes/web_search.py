from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_tavily import TavilySearch

from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState


TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
TAVILY_TOPIC = os.getenv("TAVILY_TOPIC", "general")
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")

# Trusted psychoeducation / clinical / reputable health sources only
TRUSTED_DOMAINS: List[str] = [
    "iocdf.org",
    "nimh.nih.gov",
    "nhs.uk",
    "nice.org.uk",
    "apa.org",
    "mcleanhospital.org",
    "mayoclinic.org",
    "clevelandclinic.org",
    "medlineplus.gov",
    "healthdirect.gov.au",
]


class TrustedWebSearchService:
    """
    Tavily-based restricted web search for psychoeducation fallback.

    This is only used after therapist KB retrieval is judged insufficient.
    """

    def __init__(self) -> None:
        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("TAVILY_API_KEY is not configured")

        # Official modern LangChain Tavily integration
        self.tool = TavilySearch(
            max_results=TAVILY_MAX_RESULTS,
            topic=TAVILY_TOPIC,
            search_depth=TAVILY_SEARCH_DEPTH,
            include_raw_content=True,
        )

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search trusted domains only and normalize results.
        """
        query = (query or "").strip()
        if not query:
            return []

        response = self.tool.invoke(
            {
                "query": query,
                "include_domains": TRUSTED_DOMAINS,
            }
        )

        raw_results = response.get("results", []) if isinstance(response, dict) else []

        normalized: List[Dict[str, Any]] = []
        for item in raw_results:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            content = (
                item.get("raw_content")
                or item.get("content")
                or ""
            ).strip()

            if not url or not content:
                continue

            normalized.append(
                {
                    "title": title or "Untitled",
                    "content": content,
                    "url": url,
                    "source": _extract_domain(url),
                }
            )

        return normalized


def web_search_node(state: PsychoeducationState) -> Dict[str, Any]:
    """
    Restricted Tavily fallback search.

    Inputs expected in state:
    - user_message
    - retrieval_query
    - selected_db_context_summary

    Outputs:
    - web_used
    - web_results
    - web_context_summary
    - used_sources
    """
    retrieval_query = (state.get("retrieval_query") or "").strip()
    user_message = (state.get("user_message") or "").strip()
    selected_db_context_summary = (state.get("selected_db_context_summary") or "").strip()

    query = retrieval_query or user_message
    if not query:
        return {
            "web_used": False,
            "web_results": [],
            "web_context_summary": "",
        }

    # Slightly bias the fallback query toward psychoeducation
    if selected_db_context_summary:
        query = f"{query} | psychoeducation | {selected_db_context_summary}"

    service = TrustedWebSearchService()
    results = service.search(query)

    return {
        "web_used": bool(results),
        "web_results": results,
        "web_context_summary": _build_web_context_summary(results),
    }


def _build_web_context_summary(results: List[Dict[str, Any]]) -> str:
    if not results:
        return ""

    parts: List[str] = []

    for idx, result in enumerate(results, start=1):
        title = (result.get("title") or "Untitled").strip()
        source = (result.get("source") or "unknown").strip()
        content = (result.get("content") or "").strip()

        shortened = content[:700].strip()
        if len(content) > 700:
            shortened += "..."

        parts.append(
            f"[Web Source {idx}: {title} ({source})]\n{shortened}"
        )

    return "\n\n---\n\n".join(parts)


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return (parsed.netloc or "").replace("www.", "").strip()
    except Exception:
        return "unknown"