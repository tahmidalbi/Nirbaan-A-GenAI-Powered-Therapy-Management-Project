from typing import Dict

from app.NirbaanAIPatient.PsychoeducationChatbot.graph import psychoeducation_graph
from app.NirbaanAIPatient.GeneralSupportChatbot.graph import general_support_graph
from app.NirbaanAIPatient.HumanEscalationAgent.graph import human_escalation_graph


def psychoeducation_node(state: Dict):

    result = psychoeducation_graph.invoke(state)

    return {
        "final_response": result.get("final_response", "")
    }


def general_support_node(state: Dict):

    result = general_support_graph.invoke(state)

    return {
        "final_response": result.get("final_response", "")
    }


def human_escalation_node(state: Dict):

    result = human_escalation_graph.invoke(state)

    return {
        "final_response": result.get("final_response", "")
    }