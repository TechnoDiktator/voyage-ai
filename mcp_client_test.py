
import os
import asyncio
import certifi

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# SSL configuration
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is missing")


# Initialize MCP client
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        }
    }
)


# Tool cache
tavily_search_tool = None
tool_lock = asyncio.Lock()

async def get_all_tools():
    tools = await client.get_tools()

    print("\nAvailable MCP Tools:")

    for tool in tools:
        print(f"- {tool.name}: {tool.description} \n")

    return tools



async def get_tavily_search_tool():

    global tavily_search_tool

    if tavily_search_tool is not None:
        return tavily_search_tool

    async with tool_lock:

        # Double-check after acquiring lock
        if tavily_search_tool is not None:
            return tavily_search_tool

        tools = await client.get_tools()

        for tool in tools:
            print(tool.name)

        tavily_search_tool = next(
            tool for tool in tools
            if tool.name == "tavily_search"
        )

        return tavily_search_tool


# Search function
async def tavily_mcp_search(query: str):

    search_tool = await get_tavily_search_tool()

    result = await search_tool.ainvoke(
        {
            "query": query
        }
    )
    return result






