"""LangGraph shared state for the travel-planning workflow."""

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage


class TravelState(TypedDict, total=False):
    # Reducer: new messages are appended instead of overwriting.
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str

    # Supervisor + guardrail
    guardrail_allowed: bool
    guardrail_reason: str
    selected_agents: list[str]
    trip_constraints: dict[str, Any]
    supervisor_reasoning: str

    # Specialist results
    flight_results: str
    hotel_results: str
    weather_results: str
    budget_results: str
    itinerary: str

    # Human-in-the-loop
    approval_request: str
    approved: bool
    human_feedback: str
    # Number of rejected drafts so far; capped by MAX_REVISIONS.
    revision_count: int

    final_response: str
    llm_calls: int


def empty_constraints() -> dict[str, Any]:
    """Blank trip constraints used before the supervisor fills them in."""
    return {
        "destination": "",
        "origin": "",
        "duration": "",
        "budget": "",
        "travel_style": "",
        "special_preferences": [],
    }
