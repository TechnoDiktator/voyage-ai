"""Final agent: turns the approved draft into the polished user-facing plan."""

from langchain_core.messages import HumanMessage, SystemMessage

from config import CLIP_LIMITS
from llm import llm
from state import TravelState
from utils import clip


def final_agent(state: TravelState):
    """Write the final answer, applying human feedback when it exists."""
    if state.get("approved", False):
        review_instruction = (
            "The user approved the draft. Preserve its decisions while polishing it."
        )
    else:
        review_instruction = f"""
The user requested a revision. Apply this feedback carefully:
{state.get('human_feedback', '') or 'Improve the draft before finalizing it.'}
"""

    final_prompt = f"""
Generate the final travel response for the user.

Human Review:
{review_instruction}

User Request:
{state['user_query']}

Supervisor Constraints:
{state.get('trip_constraints', {})}

Flights:
{clip(state.get('flight_results', ''), CLIP_LIMITS['flight'])}

Hotels:
{clip(state.get('hotel_results', ''), CLIP_LIMITS['hotel'])}

Weather:
{clip(state.get('weather_results', ''), CLIP_LIMITS['weather'])}

Budget Analysis:
{clip(state.get('budget_results', ''), CLIP_LIMITS['budget'])}

Draft Itinerary:
{clip(state.get('itinerary', ''), CLIP_LIMITS['itinerary'])}

Format the final answer beautifully using these sections:
1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Weather Information
5. Day-by-Day Itinerary
6. Estimated Budget
7. Final Recommendations

Day-by-day table rules (strict):
- For each day use a Markdown table with exactly these columns: | Time | Activity | Cost |
- Put the price of every priced item ONLY in the Cost column, with the currency
  (for example "INR 500"). Do not repeat the price inside the Activity text.
- Use "Free" for free items and "-" only for non-activities such as rest.
- End each day with a bold line: **Day total: <amount>**
- Use the same currency everywhere, matching the user's request.

Important:
- Be clear and practical.
- Mention that live flight APIs may not provide ticket prices when pricing is unavailable.
- Include weather-based travel advice.
- Keep the response useful for real travel planning.
- Incorporate the human feedback when revision was requested.
"""

    response = llm.invoke(
        [
            SystemMessage(content="You are a professional AI travel booking assistant."),
            HumanMessage(content=final_prompt),
        ]
    )

    return {
        "final_response": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
