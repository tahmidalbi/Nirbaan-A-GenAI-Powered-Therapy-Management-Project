# app/education/erp/graph.py
from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.education.erp.state import EducationState
from app.education.erp.kb import retrieve_kb, kb_context
from app.education.erp.web import tavily_search
from app.education.erp.llm import get_llm
from app.education.erp.schemas import KBJudge, ERPEducation
from app.education.erp.prompts import KB_JUDGE_SYSTEM, EDU_SYSTEM
from app.education.erp.config import USE_WEB_FALLBACK


def build_graph():
    llm = get_llm()

    # --------- Nodes ---------

    def kb_retrieve_node(state: EducationState) -> EducationState:
        chunks = retrieve_kb(state["therapist_id"], state["topic"])
        return {**state, "kb_chunks": chunks}

    def kb_judge_node(state: EducationState) -> EducationState:
        ctx = kb_context(state.get("kb_chunks", []))
        judge_llm = llm.with_structured_output(KBJudge, method="json_schema")

        result: KBJudge = judge_llm.invoke([
            {"role": "system", "content": KB_JUDGE_SYSTEM},
            {"role": "user", "content": f"TOPIC: {state['topic']}\n\nKB EXCERPTS:\n{ctx or '(none)'}"}
        ])
        return {
            **state,
            "kb_sufficient": bool(result.kb_sufficient),
            "kb_reason": result.reason,
        }

    def route_after_judge(state: EducationState) -> str:
        if state.get("kb_sufficient", False):
            return "generate"
        if not USE_WEB_FALLBACK:
            return "generate"
        return "web"

    def web_node(state: EducationState) -> EducationState:
        q = "exposure response prevention ERP OCD treatment how it works"
        results = tavily_search(q, k=5)
        return {**state, "web_results": results}

    def generate_node(state: EducationState) -> EducationState:
        kb_ctx = kb_context(state.get("kb_chunks", []))

        web_ctx = ""
        web_results = state.get("web_results", []) or []
        if web_results:
            parts = []
            for i, r in enumerate(web_results, 1):
                title = r.get("title") or "Untitled"
                url = r.get("url") or ""
                content = (r.get("raw_content") or r.get("content") or "")[:2000]
                parts.append(f"[WEB {i}: {title} | {url}]\n{content}\n")
            web_ctx = "\n---\n".join(parts)

        edu_llm = llm.with_structured_output(ERPEducation, method="json_schema")

        payload: ERPEducation = edu_llm.invoke([
            {"role": "system", "content": EDU_SYSTEM},
            {"role": "user", "content": (
                f"TOPIC: {state['topic']}\n\n"
                f"KB EXCERPTS (primary):\n{kb_ctx or '(none)'}\n\n"
                f"WEB EXCERPTS (only if KB insufficient):\n{web_ctx or '(none)'}\n\n"
                "Return JSON now."
            )}
        ])

        return {**state, "output_json": payload.model_dump()}

    # --------- Graph wiring ---------

    g = StateGraph(EducationState)
    g.add_node("kb_retrieve", kb_retrieve_node)
    g.add_node("kb_judge", kb_judge_node)
    g.add_node("web", web_node)
    g.add_node("generate", generate_node)

    g.set_entry_point("kb_retrieve")
    g.add_edge("kb_retrieve", "kb_judge")
    g.add_conditional_edges("kb_judge", route_after_judge, {
        "web": "web",
        "generate": "generate",
    })
    g.add_edge("web", "generate")
    g.add_edge("generate", END)

    return g.compile()
