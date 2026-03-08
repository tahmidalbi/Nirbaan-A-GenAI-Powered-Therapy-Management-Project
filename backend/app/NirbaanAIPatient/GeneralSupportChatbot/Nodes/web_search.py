from __future__ import annotations

from typing import Any, Dict, List

from langchain_community.tools.tavily_search import TavilySearchResults

from app.NirbaanAIPatient.GeneralSupportChatbot.state import (
    GeneralSupportState,
    WebResult,
)


TRUSTED_DOMAINS = [
    "iocdf.org",
    "ocduk.org",
]


def web_search_node(state: GeneralSupportState) -> Dict[str, Any]:
    """
    Perform web search fallback using Tavily restricted to trusted sources.
    """
    retrieval_query = (state.get("retrieval_query") or "").strip()

    if not retrieval_query:
        return {
            "web_used": False,
            "web_results": [],
            "web_context_summary": "",
        }

    tavily_tool = TavilySearchResults(
        max_results=6,
        include_domains=TRUSTED_DOMAINS,
    )

    results = tavily_tool.invoke({"query": retrieval_query})

    web_results: List[WebResult] = []

    for r in results:
        if isinstance(r, dict):
            content = (r.get("content") or "").strip()

            web_results.append(
                {
                    "title": r.get("title") or "Web Result",
                    "content": content,
                    "url": r.get("url"),
                    "source": r.get("url") or "web",
                }
            )
        else:
            # Some Tavily versions / wrappers may return plain strings
            web_results.append(
                {
                    "title": "Web Result",
                    "content": str(r).strip(),
                    "url": None,
                    "source": "web",
                }
            )

    web_context_summary = _build_web_context_summary(web_results)

    return {
        "web_used": bool(web_results),
        "web_results": web_results,
        "web_context_summary": web_context_summary,
    }


def _build_web_context_summary(results: List[WebResult]) -> str:
    """
    Convert web results into compact grounding context for generation.
    """
    if not results:
        return ""

    parts: List[str] = []

    for i, r in enumerate(results[:5], start=1):
        title = r.get("title") or "Unknown Source"
        text = (r.get("content") or "").strip()

        if len(text) > 400:
            text = text[:400] + "..."

        parts.append(f"[Web Source {i}: {title}]\n{text}")

    return "\n\n---\n\n".join(parts)