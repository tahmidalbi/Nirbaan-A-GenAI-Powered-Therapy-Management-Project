"""Fail-safe behaviour of the escalation path when language-model calls fail.

Every LLM is a fake, the database is in-memory SQLite, and the WebSocket
broadcaster is replaced with a recorder: no API calls, no real alerts.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import openai
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.chat.models import EPGroup, EPGroupMessage
from app.database.base import Base
from app.therapists.models import Therapist
from app.NirbaanAIPatient.CentralAgent import graph as central_graph_module
from app.NirbaanAIPatient.CentralAgent import router as router_module
from app.NirbaanAIPatient.CentralAgent import subgraph_nodes as subgraph_nodes_module
from app.NirbaanAIPatient.HumanEscalationAgent import graph as escalation_graph_module
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes import generate_helper_message as helper_module
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes import send_to_ep_group as send_module
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes import verifier as verifier_module

PATIENT_CONTEXT = {
    "patient_name": "Test Patient",
    "patient_conditions": "OCD",
    "patient_conditions_description": "",
    "patient_address": "",
    "db_obsession_compulsion_pairs": [],
    "db_latest_weekly_progress": None,
}
SUBTLE_MESSAGE = "Everything feels pointless today and I can't stop the thoughts."
CRISIS_MESSAGE = "I want to kill myself."
TIMEOUT = openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))


def fake_llm(outcome):
    """A stand-in for ChatOpenAI that raises `outcome` if it is an exception, else returns it."""

    class _Fake:
        created = []  # constructor kwargs, one entry per LLM created

        def __init__(self, *args, **kwargs):
            _Fake.created.append(kwargs)

        def with_structured_output(self, schema):
            return self

        def invoke(self, prompt):
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    return _Fake


def all_llms(monkeypatch, router=None, verifier=None, helper=None):
    fakes = {}
    for name, module, outcome in (
        ("router", router_module, router),
        ("verifier", verifier_module, verifier),
        ("helper", helper_module, helper),
    ):
        fakes[name] = fake_llm(outcome if outcome is not None else RuntimeError("API down"))
        monkeypatch.setattr(module, "ChatOpenAI", fakes[name])
    return fakes


def base_state(message):
    return {"patient_id": 1, "therapist_id": 1, "thread_id": 1, "user_message": message, "recent_chat_history": []}


# ---------- fixtures ----------

@pytest.fixture(autouse=True)
def broadcasts(monkeypatch):
    sent = []

    class _Manager:
        async def broadcast(self, group_id, payload):
            sent.append(payload)

    monkeypatch.setattr(send_module, "ep_group_manager", _Manager())
    send_module._last_fallback_alert.clear()
    yield sent
    send_module._last_fallback_alert.clear()


@pytest.fixture
def Session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Therapist.__table__, EPGroup.__table__, EPGroupMessage.__table__])
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db.add(Therapist(id=1, name="T1", email="t1@example.com", hashed_password="x",
                     license_number="L1", specialty="OCD", address="A"))
    db.commit()
    db.close()
    yield factory
    engine.dispose()


def saved_alerts(Session):
    db = Session()
    try:
        return [m.content for m in db.query(EPGroupMessage).order_by(EPGroupMessage.id).all()]
    finally:
        db.close()


@pytest.fixture
def escalation_graph(monkeypatch, Session):
    monkeypatch.setattr(escalation_graph_module, "_load_context_wrapper", lambda state: dict(PATIENT_CONTEXT))

    def send(state):
        db = Session()
        try:
            return send_module.send_to_ep_group_node(state, db)
        finally:
            db.close()

    monkeypatch.setattr(escalation_graph_module, "_send_to_ep_group_wrapper", send)
    graph = escalation_graph_module.build_human_escalation_graph.__wrapped__()
    monkeypatch.setattr(subgraph_nodes_module, "human_escalation_graph", graph)
    return graph


@pytest.fixture
def central(monkeypatch, escalation_graph):
    for name in ("psychoeducation", "general_support"):
        monkeypatch.setattr(central_graph_module, f"{name}_node", lambda state, n=name: {"final_response": n})
    return central_graph_module.build_central_graph()


# ---------- verifier ----------

def test_verifier_error_escalates_by_default(monkeypatch):
    all_llms(monkeypatch)
    result = verifier_module.verifier_node(base_state(SUBTLE_MESSAGE))
    assert result["needs_human_help"] is True
    assert result["verification_unavailable"] is True
    assert "not a confirmed crisis" in result["verifier_reasoning"]


def test_verifier_timeout_escalates_by_default(monkeypatch):
    monkeypatch.setattr(verifier_module, "ESCALATION_LLM_TIMEOUT_SECONDS", 5.0)
    fakes = all_llms(monkeypatch, verifier=TIMEOUT)
    result = verifier_module.verifier_node(base_state(SUBTLE_MESSAGE))
    assert result["needs_human_help"] is True
    assert result["verification_unavailable"] is True
    assert fakes["verifier"].created[0]["timeout"] == 5.0  # the configured limit is passed to the client


def test_verifier_negative_decision_is_kept(monkeypatch):
    no = verifier_module.VerifierOutput(needs_human_help=False, reasoning="Distressed but able to continue.")
    all_llms(monkeypatch, verifier=no)
    result = verifier_module.verifier_node(base_state(SUBTLE_MESSAGE))
    assert result == {"needs_human_help": False, "verifier_reasoning": "Distressed but able to continue."}


def test_negative_decision_sends_no_alert(monkeypatch, escalation_graph, Session):
    no = verifier_module.VerifierOutput(needs_human_help=False, reasoning="Manageable.")
    all_llms(monkeypatch, verifier=no)
    result = escalation_graph.invoke(base_state(SUBTLE_MESSAGE))
    assert saved_alerts(Session) == []
    assert "just let me know again" in result["final_response"]


# ---------- alert text ----------

def test_alert_text_error_uses_fixed_alert(monkeypatch):
    all_llms(monkeypatch)
    state = {**base_state(CRISIS_MESSAGE), **PATIENT_CONTEXT, "verifier_reasoning": "Escalated by rule."}
    message = helper_module.generate_helper_message_node(state)["helper_message"]
    assert message.startswith("URGENT")
    assert "Test Patient" in message and CRISIS_MESSAGE in message


def test_unavailable_check_uses_fixed_alert_without_llm(monkeypatch):
    fakes = all_llms(monkeypatch)
    state = {**base_state(SUBTLE_MESSAGE), **PATIENT_CONTEXT, "verification_unavailable": True}
    message = helper_module.generate_helper_message_node(state)["helper_message"]
    assert "NOT a confirmed crisis" in message
    assert fakes["helper"].created == []


def test_crisis_alert_is_saved_when_all_llms_fail(monkeypatch, escalation_graph, Session, broadcasts):
    all_llms(monkeypatch)
    result = escalation_graph.invoke(base_state(CRISIS_MESSAGE))
    alerts = saved_alerts(Session)
    assert len(alerts) == 1 and alerts[0].startswith("URGENT")
    assert result["final_response"] == send_module.ALERT_SENT_RESPONSE
    assert len(broadcasts) == 1  # recorded by the fake broadcaster only


# ---------- router ----------

def test_router_error_goes_to_escalation_check(monkeypatch):
    all_llms(monkeypatch)
    assert router_module.router_node(base_state("What is ERP?")) == {
        "route": "human_escalation",
        "router_unavailable": True,
    }


def test_router_error_with_negative_verifier_sends_no_alert(monkeypatch, central, Session):
    no = verifier_module.VerifierOutput(needs_human_help=False, reasoning="A question about ERP.")
    all_llms(monkeypatch, verifier=no)
    result = central.invoke(base_state("What is ERP?"))
    assert saved_alerts(Session) == []
    assert "trouble answering" in result["final_response"]


# ---------- timeout and retry settings ----------

# Runs in a fresh process so the environment variables are read at import time, as in production.
_RECORD_SETTINGS = """
import json
from app.NirbaanAIPatient.CentralAgent import router
from app.NirbaanAIPatient.HumanEscalationAgent.Nodes import verifier, generate_helper_message as helper

calls = {}
def recorder(name):
    class Fake:
        def __init__(self, *args, **kwargs):
            calls[name] = {"timeout": kwargs.get("timeout"), "max_retries": kwargs.get("max_retries")}
        def with_structured_output(self, schema):
            return self
        def invoke(self, prompt):
            raise RuntimeError("settings recorded; no API call")
    return Fake

for name, module in (("router", router), ("verifier", verifier), ("helper", helper)):
    module.ChatOpenAI = recorder(name)

router.router_node({"user_message": "What is ERP?"})
verifier.verifier_node({"user_message": "What is ERP?"})
helper.generate_helper_message_node({"user_message": "What is ERP?"})
print(json.dumps(calls))
"""


@pytest.mark.parametrize("env, expected", [
    ({}, {"timeout": 8.0, "max_retries": 0}),
    ({"ESCALATION_LLM_TIMEOUT_SECONDS": "3.5", "ESCALATION_LLM_MAX_RETRIES": "2"},
     {"timeout": 3.5, "max_retries": 2}),
])
def test_safety_llm_calls_use_configured_timeout_and_retries(env, expected):
    child_env = {k: v for k, v in os.environ.items() if not k.startswith("ESCALATION_LLM_")}
    child_env.update(env)
    result = subprocess.run(
        [sys.executable, "-c", _RECORD_SETTINGS],
        cwd=Path(__file__).resolve().parents[1],
        env=child_env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    calls = json.loads(result.stdout.strip().splitlines()[-1])
    assert calls == {"router": expected, "verifier": expected, "helper": expected}


# ---------- outages and delivery ----------

def test_prolonged_outage_sends_one_fallback_alert_per_patient(monkeypatch, central, Session):
    all_llms(monkeypatch)
    responses = [central.invoke(base_state(m))["final_response"] for m in ("Hello", "What is ERP?", "Are you there?")]
    alerts = saved_alerts(Session)
    assert len(alerts) == 1 and "NOT a confirmed crisis" in alerts[0]
    assert responses == [
        send_module.FALLBACK_ALERT_SENT_RESPONSE,
        send_module.FALLBACK_ALERT_RECENT_RESPONSE,
        send_module.FALLBACK_ALERT_RECENT_RESPONSE,
    ]


def test_confirmed_alert_is_not_held_back_during_outage(monkeypatch, central, Session):
    all_llms(monkeypatch)
    central.invoke(base_state("Hello"))
    result = central.invoke(base_state(CRISIS_MESSAGE))
    assert len(saved_alerts(Session)) == 2
    assert result["final_response"] == send_module.ALERT_SENT_RESPONSE


def test_patient_not_told_care_team_notified_if_alert_not_saved(Session):
    class _BrokenSession:
        def __init__(self):
            self._db = Session()

        def __getattr__(self, name):
            return getattr(self._db, name)

        def commit(self):
            raise RuntimeError("database unavailable")

    state = {**base_state(CRISIS_MESSAGE), "patient_name": "Test Patient", "helper_message": "URGENT"}
    result = send_module.send_to_ep_group_node(state, _BrokenSession())
    assert result["final_response"] == send_module.ALERT_FAILED_RESPONSE
    assert "ep_group_message_id" not in result
    assert saved_alerts(Session) == []


@pytest.mark.parametrize("response", [
    send_module.ALERT_SENT_RESPONSE,
    send_module.FALLBACK_ALERT_SENT_RESPONSE,
    send_module.FALLBACK_ALERT_RECENT_RESPONSE,
    send_module.ALERT_FAILED_RESPONSE,
])
def test_replies_do_not_promise_a_human_response(response):
    text = response.lower()
    for promise in ("reaching out", "will reach out", "soon", "has been notified", "stay where you are"):
        assert promise not in text
    assert "local emergency services" in text


@pytest.mark.parametrize("response", [
    send_module.ALERT_SENT_RESPONSE,
    send_module.FALLBACK_ALERT_SENT_RESPONSE,
    send_module.FALLBACK_ALERT_RECENT_RESPONSE,
])
def test_saved_alert_replies_say_where_the_alert_went(response):
    assert "support chat" in response


def test_patient_not_told_care_team_notified_without_therapist(Session):
    state = {**base_state(CRISIS_MESSAGE), "therapist_id": None, "helper_message": "URGENT"}
    result = send_module.send_to_ep_group_node(state, Session())
    assert result["final_response"] == send_module.ALERT_FAILED_RESPONSE
