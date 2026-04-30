import json
import os
import shutil
from pathlib import Path


# ── Tool definitions (sent to OpenAI) ────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with given content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to delete"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a folder (and any parent folders)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder path to create"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_folder",
            "description": "Delete a folder and all its contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder path to delete"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Search the Tavily API for query results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "search_depth": {
                        "type": "string",
                        "description": "Search depth preset",
                        "enum": ["ultra-fast", "fast", "basic", "advanced"],
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_folder",
            "description": "List files and folders inside a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder path to list"},
                },
                "required": ["path"],
            },
        },
    },
]


# ── Tool executor ─────────────────────────────────────────────────────────
def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "read_file":
            p = Path(args["path"])
            if not p.exists():
                return f"Error: file not found: {p}"
            return p.read_text(encoding="utf-8")

        elif name == "write_file":
            p = Path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"], encoding="utf-8")
            return f"✔ Written: {p}"

        elif name == "delete_file":
            p = Path(args["path"])
            if not p.exists():
                return f"Error: file not found: {p}"
            p.unlink()
            return f"✔ Deleted file: {p}"

        elif name == "create_folder":
            p = Path(args["path"])
            p.mkdir(parents=True, exist_ok=True)
            return f"✔ Created folder: {p}"

        elif name == "delete_folder":
            p = Path(args["path"])
            if not p.exists():
                return f"Error: folder not found: {p}"
            shutil.rmtree(p)
            return f"✔ Deleted folder: {p}"

        elif name == "tavily_search":
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return "Error: TAVILY_API_KEY not found in environment. Set it in .env or system environment."

            try:
                from tavily import TavilyClient
            except ImportError:
                return "Error: missing dependency tavily-python. Install with: pip install tavily-python"

            query = args.get("query", "")
            search_depth = args.get("search_depth", "basic")
            try:
                client = TavilyClient(api_key)
                response = client.search(query=query, search_depth=search_depth)
            except Exception as e:
                return f"Error: {e}"

            if isinstance(response, dict):
                return json.dumps(response, indent=2)
            return str(response)

        elif name == "list_folder":
            p = Path(args["path"])
            if not p.exists():
                return f"Error: folder not found: {p}"
            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name))
            lines = []
            for e in entries:
                icon = "📄" if e.is_file() else "📁"
                lines.append(f"{icon} {e.name}")
            return "\n".join(lines) if lines else "(empty)"

        else:
            return f"Error: unknown tool '{name}'"

    except Exception as e:
        return f"Error: {e}"