"""Itinerary agent: merges specialist results into a draft for human review."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import CLIP_LIMITS, MAX_REVISIONS
from llm import llm
from state import TravelState
from utils import clip


def itinerary_agent(state: TravelState):
    """Create (or revise) the draft itinerary that the human will review."""
    # On a revision round, show the model the previous draft and the user's feedback.
    revision_block = ""
    if state.get("human_feedback") and state.get("itinerary"):
        revision_block = f"""
Previous Draft (to revise):
{clip(state['itinerary'], CLIP_LIMITS['previous_draft'])}

User Feedback (apply this to the new draft):
{state['human_feedback']}
"""

    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}

Trip Constraints:
{state.get('trip_constraints', {})}

Flight Results:
{clip(state.get('flight_results', ''), CLIP_LIMITS['flight'])}

Hotel Results:
{clip(state.get('hotel_results', ''), CLIP_LIMITS['hotel'])}

Weather Results:
{clip(state.get('weather_results', ''), CLIP_LIMITS['weather'])}

Budget Results:
{clip(state.get('budget_results', ''), CLIP_LIMITS['budget'])}
{revision_block}
Make the itinerary practical, budget-aware, and easy to follow.
Create a clear draft that is ready for human review.
"""

    response = llm.invoke(
        [
            SystemMessage(content="You are an expert travel planner."),
            HumanMessage(content=prompt),
        ]
    )

    revision_count = state.get("revision_count", 0)
    if revision_count:
        approval_request = (
            f"Revision {revision_count} of {MAX_REVISIONS}: the draft was updated "
            "with your feedback. Approve it, or request another change."
        )
    else:
        approval_request = (
            "Please review the generated draft itinerary. Approve it to create the "
            "final polished plan, or provide feedback for revision."
        )

    return {
        "itinerary": response.content,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
