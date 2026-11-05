import asyncio

from mcp_client_test import get_all_tools , tavily_mcp_search


# from tools.tavily_tool import tavily_search

# from tools.flight_tool import search_flights


# from backend import run_travel_agent

# # res = tavily_search("Best hotels in India")

# # print(res)

# res = search_flights("Search flights from New York to London")
# print(res)

# final_res = run_travel_agent("Search flights from New York to London and find hotels" , thread_id="test_thread")
# print(final_res)


if __name__ == "__main__" :
    result = asyncio.run(tavily_mcp_search("give me the latest news on bugatti"))
    print(result)



