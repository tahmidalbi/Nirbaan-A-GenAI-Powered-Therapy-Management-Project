"""Therapist passages rejected by the sufficiency check are not used to answer.

The answer LLM is a recording fake; in the flow tests, retrieval, the sufficiency
check, and web search are also fakes, so no API or database calls are made.
"""

import pytest

from app.NirbaanAIPatient.PsychoeducationChatbot import graph as psy_graph_module
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes import generate as generate_module
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.generate import (
    INSUFFICIENT_INFORMATION_RESPONSE,
    WEB_SOURCE_DISCLOSURE,
    GenerateOutput,
    generate_node,
)

QUESTION = "What is ERP?"
ANSWER = "ERP means facing feared situations step by step without doing compulsions."
REJECTED_CHUNK = {"content": "A passage about sleep routines.", "source": "Sleep handout"}
GOOD_CHUNK = {"content": "ERP is a behavioural treatment for OCD.", "source": "Therapist handout"}
WEB_RESULT = {"title": "What is ERP?", "source": "iocdf.org", "content": "ERP is a treatment for OCD."}


class _RecordingLLM:
    prompts = []

    def with_structured_output(self, schema):
        return self

    def invoke(self, prompt):
        _RecordingLLM.prompts.append(prompt)
        return GenerateOutput(final_response=ANSWER)


@pytest.fixture
def llm(monkeypatch):
    _RecordingLLM.prompts = []
    monkeypatch.setattr(generate_module, "_get_llm", lambda: _RecordingLLM())
    return _RecordingLLM


# ---------- answer step ----------

def test_rejected_material_and_no_web_gives_fixed_reply(llm):
    result = generate_node({
        "user_message": QUESTION,
        "kb_chunks": [REJECTED_CHUNK],
        "retrieval_sufficient": False,
        "web_used": False,
        "web_results": [],
    })
    assert result["final_response"] == INSUFFICIENT_INFORMATION_RESPONSE
    assert llm.prompts == []  # no answer is generated


def test_web_answer_does_not_use_rejected_material(llm):
    result = generate_node({
        "user_message": QUESTION,
        "kb_chunks": [REJECTED_CHUNK],
        "retrieval_sufficient": False,
        "web_used": True,
        "web_results": [WEB_RESULT],
    })
    prompt = llm.prompts[0]
    assert WEB_RESULT["content"] in prompt
    assert REJECTED_CHUNK["content"] not in prompt
    assert result["used_sources"] == [WEB_RESULT["title"]]
    assert result["final_response"] == f"{ANSWER}\n\n{WEB_SOURCE_DISCLOSURE}"


def test_sufficient_material_is_used_as_before(llm):
    result = generate_node({
        "user_message": QUESTION,
        "kb_chunks": [GOOD_CHUNK],
        "retrieval_sufficient": True,
        "web_used": False,
        "web_results": [],
    })
    assert GOOD_CHUNK["content"] in llm.prompts[0]
    assert result["final_response"] == ANSWER
    assert result["used_sources"] == [GOOD_CHUNK["source"]]


# ---------- full psychoeducation flow ----------

def _build_flow(monkeypatch, *, sufficient, web_results):
    steps = []

    def kb_retrieval(state):
        steps.append("search")
        return {"kb_chunks": [GOOD_CHUNK if sufficient else REJECTED_CHUNK]}

    def check(state):
        steps.append("check")
        return {"retrieval_sufficient": sufficient, "retry_count": int(state.get("retry_count", 0)) + (0 if sufficient else 1)}

    def web_search(state):
        steps.append("web")
        return {"web_used": bool(web_results), "web_results": web_results}

    monkeypatch.setattr(psy_graph_module, "db_picker_node", lambda state, db: {})
    monkeypatch.setattr(psy_graph_module, "session_summarizer_node", lambda state: {})
    monkeypatch.setattr(psy_graph_module, "kb_retrieval_node", kb_retrieval)
    monkeypatch.setattr(psy_graph_module, "sufficiency_checker_node", check)
    monkeypatch.setattr(psy_graph_module, "web_search_node", web_search)
    return psy_graph_module.build_psychoeducation_graph(), steps


def test_flow_two_rejected_searches_and_empty_web_gives_fixed_reply(monkeypatch, llm):
    graph, steps = _build_flow(monkeypatch, sufficient=False, web_results=[])
    result = graph.invoke({"user_message": QUESTION, "therapist_id": 1})
    assert steps == ["search", "check", "search", "check", "web"]  # first search, second search, web fallback
    assert result["final_response"] == INSUFFICIENT_INFORMATION_RESPONSE
    assert llm.prompts == []


def test_flow_with_sufficient_material_is_unchanged(monkeypatch, llm):
    graph, steps = _build_flow(monkeypatch, sufficient=True, web_results=[])
    result = graph.invoke({"user_message": QUESTION, "therapist_id": 1})
    assert steps == ["search", "check"]
    assert result["final_response"] == ANSWER
    assert GOOD_CHUNK["content"] in llm.prompts[0]
