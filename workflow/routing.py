"""Routing functions that decide which node runs next."""

from config import AGENT_ORDER, MAX_REVISIONS
from state import TravelState

ROUTE_MAP = {
    "guardrail_blocked": "guardrail_blocked",
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
}


def _selected_agents(state: TravelState) -> list[str]:
    selected = state.get("selected_agents", [])
    return [agent for agent in AGENT_ORDER if agent in selected]


def route_from_supervisor(state: TravelState) -> str:
    """Go to the guardrail refusal, or the first selected specialist."""
    if not state.get("guardrail_allowed", True):
        return "guardrail_blocked"

    selected = _selected_agents(state)
    return selected[0] if selected else "itinerary_agent"


def route_after_agent(current_agent: str):
    """Build a router that skips to the next selected specialist."""

    def route(state: TravelState) -> str:
        selected = _selected_agents(state)
        current_index = AGENT_ORDER.index(current_agent)

        for next_agent in AGENT_ORDER[current_index + 1 :]:
            if next_agent in selected:
                return next_agent

        return "itinerary_agent"

    return route


def route_after_approval(state: TravelState) -> str:
    """Loop back to the itinerary until approved or the revision cap is hit."""
    if state.get("approved", False):
        return "final_agent"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        return "final_agent"
    return "itinerary_agent"
