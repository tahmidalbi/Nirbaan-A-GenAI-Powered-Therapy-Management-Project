import pytest

from app.NirbaanAIPatient.HumanEscalationAgent.Nodes.verifier import (
    explicit_escalation_reason,
    verifier_node,
)

# Wordings deliberately different from evaluation/data/latency_messages.json.
EXPLICIT_REQUESTS = [
    "Could I please speak with a real human?",
    "I'd like to talk to a person instead of this bot.",
    "Call my support team, something is very wrong.",
    "Somebody please come over, I can't cope.",
    "I am in a crisis right now.",
    "I'm thinking about suicide.",
    "I don't feel safe tonight.",
    "This is an emergency.",
    "Notify the emergency team please.",
    "I need a person to call me back.",
]

# OCD-style intrusive thoughts and reassurance seeking: these must reach the LLM verifier.
AMBIGUOUS_OCD_MESSAGES = [
    "What if I hurt my baby? I would never want to.",
    "I'm scared I might hurt myself, I don't want to, the thought just won't stop.",
    "Can you tell me again that I'm a good person?",
    "My care team said I should keep doing exposures.",
    "Do you think my therapist is disappointed in me?",
    "I keep checking whether I locked the door, is that normal?",
    "What if I'm secretly a dangerous person?",
    "I feel like I'm losing my mind with these thoughts.",
]


@pytest.mark.parametrize("message", EXPLICIT_REQUESTS)
def test_explicit_requests_escalate_by_rule(message):
    assert explicit_escalation_reason(message) is not None


@pytest.mark.parametrize("message", AMBIGUOUS_OCD_MESSAGES)
def test_ambiguous_ocd_messages_are_left_to_llm(message):
    assert explicit_escalation_reason(message) is None


def test_verifier_escalates_without_calling_llm():
    result = verifier_node({"user_message": "I'm in crisis, please send someone."})
    assert result["needs_human_help"] is True
