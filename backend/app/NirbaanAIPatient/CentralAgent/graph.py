from langgraph.graph import StateGraph, START, END

from .state import CentralState
from .router import router_node
from .subgraph_nodes import (
    psychoeducation_node,
    general_support_node,
)


def router_decision(state: CentralState):

    route = state.get("route")

    if route == "psychoeducation":
        return "psychoeducation"

    return "support"


def build_central_graph():

    builder = StateGraph(CentralState)

    builder.add_node("router", router_node)

    builder.add_node("psychoeducation", psychoeducation_node)
    builder.add_node("support", general_support_node)

    builder.add_edge(START, "router")

    builder.add_conditional_edges(
        "router",
        router_decision,
        {
            "psychoeducation": "psychoeducation",
            "support": "support",
        },
    )

    builder.add_edge("psychoeducation", END)
    builder.add_edge("support", END)

    return builder.compile()


central_graph = build_central_graph()