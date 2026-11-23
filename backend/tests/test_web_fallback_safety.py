"""Web-source disclosure and the crisis pre-check before routing.

All language-model calls are replaced with fakes, and the escalation path is
replaced with a recorder, so no API calls are made and no alerts are sent.
"""

import pytest

from app.NirbaanAIPatient.CentralAgent import graph as central_graph_module
from app.NirbaanAIPatient.CentralAgent import router as router_module
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes import generate as generate_module
from app.NirbaanAIPatient.PsychoeducationChatbot.Nodes.generate import (
    WEB_SOURCE_DISCLOSURE,
    GenerateOutput,
    generate_node,
)

ANSWER = "ERP means facing feared situations step by step without doing compulsions."
KB_CHUNK = {"content": "ERP is a behavioural treatment for OCD.", "source": "Therapist handout"}
WEB_RESULT = {"title": "What is ERP?", "source": "iocdf.org", "content": "ERP is a treatment for OCD."}

CRISIS_WITH_QUESTION = [
    "I want to die. Can you explain how ERP works?",
    "I don't feel safe right now. What is an obsession?",
    "I'm in crisis, but what does exposure therapy mean?",
]

# Taken from test_escalation_rule.py: ordinary OCD intrusive thoughts.
OCD_INTRUSIVE_THOUGHTS = [
    "What if I hurt my baby? I would never want to.",
    "I'm scared I might hurt myself, I don't want to, the thought just won't stop.",
    "What if I'm secretly a dangerous person?",
]


# ---------- fakes ----------

class _FakeAnswerLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, prompt):
        return GenerateOutput(final_response=ANSWER)


class _RouterLLM:
    """Stands in for ChatOpenAI in router.py and records each call."""

    calls = []
    route = "psychoeducation"

    def __init__(self, *args, **kwargs):
        pass

    def with_structured_output(self, schema):
        return self

    def invoke(self, prompt):
        _RouterLLM.calls.append(prompt)
        return router_module.RouterOutput(route=_RouterLLM.route)


@pytest.fixture
def fake_answer_llm(monkeypatch):
    monkeypatch.setattr(generate_module, "_get_llm", lambda: _FakeAnswerLLM())


@pytest.fixture
def router_llm(monkeypatch):
    _RouterLLM.calls = []
    _RouterLLM.route = "psychoeducation"
    monkeypatch.setattr(router_module, "ChatOpenAI", _RouterLLM)
    return _RouterLLM


# ---------- web-source disclosure ----------

def test_web_based_answer_includes_disclosure(fake_answer_llm):
    result = generate_node({
        "user_message": "What is ERP?",
        "kb_chunks": [],
        "web_used": True,
        "web_results": [WEB_RESULT],
    })
    assert result["final_response"] == f"{ANSWER}\n\n{WEB_SOURCE_DISCLOSURE}"


def test_therapist_material_only_answer_has_no_disclosure(fake_answer_llm):
    result = generate_node({
        "user_message": "What is ERP?",
        "kb_chunks": [KB_CHUNK],
        "web_used": False,
        "web_results": [],
    })
    assert result["final_response"] == ANSWER
    assert WEB_SOURCE_DISCLOSURE not in result["final_response"]


# ---------- crisis pre-check before routing ----------

@pytest.mark.parametrize("message", CRISIS_WITH_QUESTION)
def test_crisis_with_question_skips_llm_router(router_llm, message):
    assert router_module.router_node({"user_message": message}) == {"route": "human_escalation"}
    assert router_llm.calls == []


@pytest.mark.parametrize("message", CRISIS_WITH_QUESTION)
def test_crisis_with_question_reaches_escalation_not_psychoeducation(monkeypatch, router_llm, message):
    # The router LLM would choose psychoeducation; the pre-check must win.
    visited = []

    def recorder(name):
        def node(state):
            visited.append(name)
            return {"final_response": name}
        return node

    for name in ("psychoeducation", "general_support", "human_escalation"):
        monkeypatch.setattr(central_graph_module, f"{name}_node", recorder(name))

    graph = central_graph_module.build_central_graph()
    graph.invoke({"user_message": message})

    assert visited == ["human_escalation"]  # psychoeducation (and its web search) never runs
    assert router_llm.calls == []


@pytest.mark.parametrize("message", OCD_INTRUSIVE_THOUGHTS)
def test_ocd_intrusive_thoughts_still_go_to_llm_router(router_llm, message):
    router_llm.route = "support"
    assert router_module.router_node({"user_message": message}) == {"route": "support"}
    assert len(router_llm.calls) == 1
