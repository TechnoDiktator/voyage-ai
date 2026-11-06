"""Human-in-the-loop approval step built on LangGraph's interrupt()."""

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from state import TravelState


def human_approval_agent(state: TravelState):
    """Pause the graph until a human approves or requests a revision."""
    # Do not wrap interrupt() in try/except. LangGraph uses it to pause execution.
    review = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "selected_agents": state.get("selected_agents", []),
            "supervisor_reasoning": state.get("supervisor_reasoning", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional revision feedback",
            },
        }
    )

    approved = bool(review.get("approved", False))
    human_feedback = str(review.get("feedback", "")).strip()
    revision_count = state.get("revision_count", 0)

    return {
        "approved": approved,
        "human_feedback": human_feedback,
        # Each rejection consumes one revision round.
        "revision_count": revision_count if approved else revision_count + 1,
        "messages": [AIMessage(content="Human approval step completed.")],
    }
