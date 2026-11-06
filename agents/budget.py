"""Budget agent: judges whether the trip fits the user's budget."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import CLIP_LIMITS
from llm import llm
from state import TravelState
from utils import clip


def budget_agent(state: TravelState):
    """Estimate costs and feasibility from the earlier specialist results."""
    prompt = f"""
Analyze whether this trip is realistic for the user's budget.

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

Return:
1. Estimated cost categories
2. Budget risk areas
3. Money-saving suggestions
4. Overall feasibility

If exact live prices are unavailable, clearly label estimates as approximate.
"""

    response = llm.invoke(
        [
            SystemMessage(content="You are a practical travel budget analyst."),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "budget_results": response.content,
        "messages": [AIMessage(content="Budget assessment generated.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
