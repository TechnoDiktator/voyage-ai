"""Assembles the LangGraph workflow from the agents and routing rules."""

from langgraph.graph import END, START, StateGraph

from agents import (
    budget_agent,
    final_agent,
    flight_agent,
    guardrail_blocked_agent,
    hotel_agent,
    human_approval_agent,
    itinerary_agent,
    supervisor_agent,
    weather_agent,
)
from state import TravelState
from workflow.persistence import create_checkpointer
from workflow.routing import (
    ROUTE_MAP,
    route_after_agent,
    route_after_approval,
    route_from_supervisor,
)


def build_graph() -> StateGraph:
    """Create the (uncompiled) travel-planning graph."""
    graph = StateGraph(TravelState)

    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("guardrail_blocked", guardrail_blocked_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("budget_agent", budget_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    graph.add_node("human_approval", human_approval_agent)
    graph.add_node("final_agent", final_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, ROUTE_MAP)

    for name in ("flight_agent", "hotel_agent", "weather_agent", "budget_agent"):
        graph.add_conditional_edges(name, route_after_agent(name), ROUTE_MAP)

    graph.add_edge("itinerary_agent", "human_approval")
    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"itinerary_agent": "itinerary_agent", "final_agent": "final_agent"},
    )
    graph.add_edge("final_agent", END)
    graph.add_edge("guardrail_blocked", END)

    return graph


def compile_graph():
    """Compile the graph with the Postgres checkpointer attached."""
    return build_graph().compile(checkpointer=create_checkpointer())
