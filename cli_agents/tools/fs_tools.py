import json
from pathlib import Path
from typing import List

from cli_agents.utils import should_ignore


READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file in the repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read."},
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create or overwrite a file with the provided content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path."},
                "content": {"type": "string", "description": "File contents."},
            },
            "required": ["path", "content"],
        },
    },
}

LIST_FOLDER_TOOL = {
    "type": "function",
    "function": {
        "name": "list_folder",
        "description": "List files and directories inside a folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list."},
            },
            "required": ["path"],
        },
    },
}

SEARCH_PROJECT_TOOL = {
    "type": "function",
    "function": {
        "name": "search_project",
        "description": "Search repository files for a keyword or pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text or pattern to search for."},
                "root": {"type": "string", "description": "Optional root path to search."},
            },
            "required": ["query"],
        },
    },
}


def read_file(path: str) -> str:
    target = Path(path)
    if not target.exists():
        return f"Error: file not found: {target}"

    try:
        return target.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading file: {exc}"


def write_file(path: str, content: str) -> str:
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"✔ Written: {target}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def list_folder(path: str) -> str:
    target = Path(path)
    if not target.exists() or not target.is_dir():
        return f"Error: folder not found: {target}"

    entries = sorted(target.iterdir(), key=lambda entry: (entry.is_file(), entry.name))
    lines: List[str] = []
    for entry in entries:
        prefix = "📄" if entry.is_file() else "📁"
        lines.append(f"{prefix} {entry.name}")
    return "\n".join(lines) if lines else "(empty)"


def search_project(query: str, root: str | None = None) -> str:
    root_path = Path(root or Path.cwd()).resolve()
    if not root_path.exists() or not root_path.is_dir():
        return f"Error: root path not found: {root_path}"

    results: List[dict] = []
    for path in root_path.rglob("*"):
        if path.is_dir() or should_ignore(path.name):
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini"}:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        if query.lower() in content.lower() or query.lower() in path.name.lower():
            excerpt = "".join(
                line for line in content.splitlines(True) if query.lower() in line.lower()
            )[:400]
            results.append({
                "path": str(path.relative_to(root_path)),
                "excerpt": excerpt,
            })

    if not results:
        return f"No matches found for '{query}'."
    return json.dumps(results, indent=2)
