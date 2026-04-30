import json
import os

TAVILY_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "tavily_search",
        "description": "Search the Tavily API for knowledge retrieval.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text."},
                "search_depth": {
                    "type": "string",
                    "description": "Tavily search depth preset.",
                    "enum": ["ultra-fast", "fast", "basic", "advanced"],
                },
            },
            "required": ["query"],
        },
    },
}


def tavily_search(query: str, search_depth: str = "basic") -> str:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return "Error: TAVILY_API_KEY not configured."

    try:
        from tavily import TavilyClient
    except ImportError:
        return "Error: missing dependency tavily-python. Install with: pip install tavily-python"

    try:
        client = TavilyClient(api_key)
        response = client.search(query=query, search_depth=search_depth)
    except Exception as exc:
        return f"Error: {exc}"

    if isinstance(response, dict):
        return json.dumps(response, indent=2)
    return str(response)
