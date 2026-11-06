"""Hotel agent: searches for accommodation through the Tavily MCP server."""

import asyncio

from langchain_core.messages import AIMessage

from mcp_client import tavily_mcp_search
from state import TravelState


def hotel_agent(state: TravelState):
    """Run a live hotel search, falling back to general guidance on failure."""
    query = f"Best hotels for {state['user_query']}"

    try:
        hotel_results = asyncio.run(tavily_mcp_search(query))
    except Exception as exc:
        print(f"HOTEL AGENT MCP ERROR: {type(exc).__name__}: {exc}", flush=True)
        hotel_results = (
            "Live hotel search is temporarily unavailable. "
            "Provide general accommodation and neighborhood "
            "guidance based on the destination and clearly "
            "label it as non-live advice."
        )

    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel information processed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
