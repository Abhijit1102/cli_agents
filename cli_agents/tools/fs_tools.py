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

ANALYZE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_image",
        "description": "Analyze an image file and return metadata, dimensions, format, and basic structure details.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Image file path to analyze."},
            },
            "required": ["path"],
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


def analyze_image(path: str) -> str:
    target = Path(path)
    if not target.exists():
        return f"Error: file not found: {target}"
    if not target.is_file():
        return f"Error: path is not a file: {target}"

    try:
        from PIL import Image
    except ImportError:
        return "Error: missing dependency Pillow. Install with: pip install Pillow"

    try:
        if target.suffix.lower() in {".svg", ".svgz"}:
            text = target.read_text(encoding="utf-8", errors="replace")
            shapes = text.count("<path") + text.count("<rect") + text.count("<circle") + text.count("<line")
            return (
                f"format: SVG\n"
                f"size: {target.stat().st_size} bytes\n"
                f"element counts: paths={text.count('<path')}, rects={text.count('<rect')}, circles={text.count('<circle')}, lines={text.count('<line')}\n"
                f"shape summary: {shapes} vector elements"
            )

        with Image.open(target) as image:
            info = image.info or {}
            frames = getattr(image, "n_frames", 1)
            metadata_lines = [
                f"format: {image.format}",
                f"size: {image.width}x{image.height}",
                f"mode: {image.mode}",
                f"frames: {frames}",
            ]

            if info:
                metadata_lines.append(f"info: {json.dumps(info, default=str, indent=2)}")

            if image.mode == "P" and image.palette:
                metadata_lines.append(f"palette mode: {image.palette.mode}")

            try:
                exif_data = image._getexif() or {}
                if exif_data:
                    metadata_lines.append(f"exif: {json.dumps({str(k): str(v) for k, v in exif_data.items()}, indent=2)}")
            except Exception:
                pass

            return "\n".join(metadata_lines)
    except Exception as exc:
        return f"Error analyzing image: {exc}"
