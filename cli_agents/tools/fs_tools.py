import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from cli_agents.config.global_config import get_config
from cli_agents.utils import should_ignore
from cli_agents.utils.search import search_project_rg
from cli_agents.utils.fs.tree import build_tree

from .registry import tool

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@tool(
    name="read_file",
    description="Read the contents of a file. Supports reading specific line ranges for large files.",
)
def read_file(
    path: str, start_line: int | None = 1, end_line: int | None = None
) -> str:
    target = Path(path)
    if not target.exists():
        return f"Error: file not found: {target}"

    try:
        if start_line is None and end_line is None:
            # Read full file (with safety check for extreme sizes)
            if target.stat().st_size > 1_000_000:  # 1MB limit for full read
                return (
                    f"Error: File is too large ({target.stat().st_size} bytes) to read entirely. "
                    f"Please use start_line and end_line."
                )
            return target.read_text(encoding="utf-8")

        # Read specific lines
        lines = target.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)

        s = max(0, (start_line or 1) - 1)
        e = end_line or total_lines

        selected = lines[s:e]
        header = (
            f"--- Reading lines {s + 1} to {min(e, total_lines)} of {total_lines} ---\n"
        )
        return header + "\n".join(selected)

    except Exception as exc:
        return f"Error reading file: {exc}"


@tool(
    name="get_file_info",
    description="Get metadata for a specific file, including byte size and total line count.",
)
def get_file_info(path: str) -> str:
    target = Path(path)
    if not target.exists():
        return f"Error: file not found: {target}"

    try:
        stats = target.stat()
        size = stats.st_size

        line_count = 0
        if target.is_file():
            with open(target, "rb") as f:
                for _ in f:
                    line_count += 1

        return f"File: {target.name}\nSize: {size} bytes\nLines: {line_count}"
    except Exception as exc:
        return f"Error getting file info: {exc}"


@tool(
    name="write_file",
    description="Write or overwrite content to a file at the given path. Creates parent directories if they do not exist. ALWAYS provide both 'path' and 'content'.",
)
def write_file(path: str, content: str) -> str:
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"✔ Written: {target}"
    except Exception as exc:
        return f"Error writing file: {exc}"


@tool(
    name="list_folder",
    description="List all files and subdirectories in a directory, ignoring hidden/ignored files.",
)
def list_folder(path: str) -> str:
    target = Path(path)
    if not target.exists() or not target.is_dir():
        return f"Error: folder not found: {target}"
