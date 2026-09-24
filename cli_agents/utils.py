import os
import ast
from pathlib import Path
from openai import AsyncOpenAI
import seedir as sd

# ── directories to never descend into ─────────────────────────────────────
IGNORE_DIRS: set[str] = {
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env", 
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov", 
    ".eggs", "node_modules", ".next", ".nuxt", ".output", ".svelte-kit", 
    ".turbo", ".parcel-cache", "dist", "build", "out", "target", "bin", 
    "obj", ".cache", ".idea", ".vscode", ".fleet", ".DS_Store", 
    "coverage", ".nyc_output", ".terraform", ".vagrant", ".sandbox",
}

IGNORE_FILES: set[str] = {
    "uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json", 
    "yarn.lock", "pnpm-lock.yaml", "Gemfile.lock", "Cargo.lock", 
    "composer.lock", ".DS_Store", "Thumbs.db", "desktop.ini", 
    "bash.exe.stackdump", "*.pyc", "*.pyo", "*.pyd",
}

IGNORE_PREFIXES: tuple[str, ...] = (".env", "~")
IGNORE_SUFFIXES: tuple[str, ...] = (
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".o", ".a", 
    ".lib", ".class", ".jar", ".war", ".wasm", ".png", ".jpg", ".jpeg", 
    ".gif", ".ico", ".svg", ".webp", ".avif", ".mp4", ".mp3", ".wav", 
    ".ogg", ".ttf", ".otf", ".woff", ".woff2", ".eot", ".zip", ".tar", 
    ".gz", ".bz2", ".xz", ".7z", ".rar", ".db", ".sqlite", ".sqlite3", 
    ".pkl", ".h5", ".parquet", ".pdf", ".docx", ".xlsx", ".pptx", 
    ".swp", ".swo", ".bak", ".orig", ".stackdump", ".wsb",
)

def should_ignore(name: str, *, is_dir: bool = False) -> bool:
    if name.startswith(IGNORE_PREFIXES):
        return True
    if is_dir:
        return name in IGNORE_DIRS
    return name in IGNORE_FILES or name.endswith(IGNORE_SUFFIXES)

def get_file_summary(path: Path) -> str:
    """Extracts classes and functions from a Python file for AI context."""
    if path.suffix != '.py':
        return ""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        summaries = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                summaries.append(f"class {node.name}")
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef):
                        summaries.append(f"  - method {subnode.name}")
            elif isinstance(node, ast.FunctionDef):
                summaries.append(f"def {node.name}")
        return " [" + ", ".join(summaries) + "]" if summaries else ""
    except Exception:
        return ""

def build_tree(start: str | os.PathLike = ".", prefix: str = "", include_summaries: bool = False) -> list[str]:
    """
    Builds a project tree. If include_summaries is False, it uses seedir for speed.
    If True, it uses a custom traversal to append AST summaries to Python files.
    """
    if not include_summaries:
        # Use seedir for a fast, clean tree string
        tree_str = sd.seedir(
            path=start,
            style="lines",
            printout=False,
            exclude_folders=list(IGNORE_DIRS),
            exclude_files=list(IGNORE_FILES),
        )
        return tree_str.splitlines()

    # Custom traversal for summaries
    start_path = Path(start).resolve()
    try:
        entries = sorted(os.listdir(start_path))
    except PermissionError:
        return []

    result = []
    filtered = [
        e for e in entries 
        if not should_ignore(e, is_dir=os.path.isdir(os.path.join(start_path, e)))
    ]

    for i, item in enumerate(filtered):
        path = start_path / item
        is_dir = path.is_dir()
        connector = "└── " if i == len(filtered) - 1 else "├── "
        
        line = prefix + connector + item
        if not is_dir:
            line += get_file_summary(path)
            
        result.append(line)

        if is_dir:
            extension = "    " if i == len(filtered) - 1 else "│   "
            result.extend(build_tree(path, prefix + extension, include_summaries=include_summaries))

    return result

async def generate_project_description(
    project_root: Path,
    client: AsyncOpenAI,
    model: str,
) -> Path:
    output_dir = project_root / ".cli_agents"
    output_path = output_dir / "PROJECT_DESCRIPTION.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_chunks: list[str] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]
        for fname in sorted(files):
            if should_ignore(fname, is_dir=False):
                continue
            abs_path = Path(root) / fname
            rel_path = abs_path.relative_to(project_root)
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            if len(content) > 200_000:
                file_chunks.append(f"### {rel_path}\n*(file too large – skipped)*\n")
                continue
            file_chunks.append(f"### {rel_path}\n```\n{content}\n```\n")

    tree_lines = build_tree(project_root, include_summaries=True)
    tree_str = project_root.name + "/"
    if tree_lines:
        tree_str += "\n" + "\n".join(tree_lines)

    user_message = (
        f"Project tree (with symbols):\n```\n{tree_str}\n```\n\n"
        "File contents:\n\n" + "\n".join(file_chunks) + "\n\n---\n"
        "Write a thorough PROJECT_DESCRIPTION.md for this codebase.\n"
        "Cover: purpose, architecture, module breakdown, key classes/functions,\n"
        "data-flow, configuration, and how to run / extend the project."
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a senior software engineer. Output only valid Markdown."},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4096,
    )
    description_md = response.choices[0].message.content.strip()
    output_path.write_text(description_md, encoding="utf-8")
    return output_path
