import json
from cli_agents.config import AppConfig


TAVILY_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "tavily_search",
        "description": "Search the Tavily API for knowledge retrieval.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "search_depth": {
                    "type": "string",
                    "enum": ["ultra-fast", "fast", "basic", "advanced"],
                },
            },
            "required": ["query"],
        },
    },
}


def tavily_search(query: str, config: AppConfig, search_depth: str = "basic") -> str:
    api_key = config.tavily_api_key

    if not api_key:
        return "Error: TAVILY_API_KEY not configured."

    try:
        from tavily import TavilyClient
    except ImportError:
        return "Error: missing dependency tavily-python."

    try:
        client = TavilyClient(api_key)
        response = client.search(query=query, search_depth=search_depth)
    except Exception as exc:
        return f"Error: {exc}"

    return json.dumps(response, indent=2)