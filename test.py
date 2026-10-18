from tools.tavily_tool import tavily_search

from tools.flight_tool import search_flights

# res = tavily_search("Best hotels in India")

# print(res)

res = search_flights("Search flights from New York to London")
print(res)
