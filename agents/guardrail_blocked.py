"""Terminal node used when the input guardrail rejects a request."""

from langchain_core.messages import AIMessage

from state import TravelState


def guardrail_blocked_agent(state: TravelState):
    """Return the guardrail's refusal message as the final response."""
    reason = state.get("final_response") or state.get("guardrail_reason") or (
        "This request was blocked by the travel input guardrail."
    )
    return {
        "final_response": reason,
        "messages": [AIMessage(content=reason)],
    }
