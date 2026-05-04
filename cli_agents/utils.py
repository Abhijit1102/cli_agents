import os
import asyncio
from pathlib import Path
from openai import AsyncOpenAI

# ── directories to never descend into ─────────────────────────────────────
IGNORE_DIRS: set[str] = {
    # version control
    ".git", ".hg", ".svn",

    # python
    "__pycache__", ".venv", "venv", "env", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "htmlcov", ".eggs",

    # node / js
    "node_modules", ".next", ".nuxt", ".output", ".svelte-kit",
    ".turbo", ".parcel-cache",

    # build outputs
    "dist", "build", "out", "target", "bin", "obj",

    # caches / tooling
    ".cache", ".idea", ".vscode", ".fleet", ".DS_Store",
    "coverage", ".nyc_output",

    # docker / infra
    ".terraform", ".vagrant",

    # sandbox (your own tooling)
    ".sandbox",
}

# ── exact filenames to skip ────────────────────────────────────────────────
IGNORE_FILES: set[str] = {
    # locks
    "uv.lock", "poetry.lock", "Pipfile.lock",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile.lock", "Cargo.lock", "composer.lock",

    # generated / binary
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "bash.exe.stackdump",  # your repo has this

    # compiled python
    "*.pyc", "*.pyo", "*.pyd",
}

# ── prefixes: skip any file/dir whose name starts with these ──────────────
IGNORE_PREFIXES: tuple[str, ...] = (
    ".env",       # .env  .env.local  .env.production …
    "~",           # editor swap / backup files
)

# ── suffixes: skip any file whose name ends with these ────────────────────
IGNORE_SUFFIXES: tuple[str, ...] = (
    # compiled / binary
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe",
    ".o", ".a", ".lib", ".class", ".jar", ".war", ".wasm",

    # media / assets (useless as text)
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".webp", ".avif", ".mp4", ".mp3", ".wav", ".ogg",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",

    # data blobs
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".db", ".sqlite", ".sqlite3", ".pkl", ".h5", ".parquet",

    # documents (not code)
    ".pdf", ".docx", ".xlsx", ".pptx",

    # editor / OS noise
    ".swp", ".swo", ".bak", ".orig", ".stackdump",

    # sandbox / Windows Sandbox
    ".wsb",
)


def should_ignore(name: str, *, is_dir: bool = False) -> bool:
    """Return True if this file or directory should be excluded."""
    if name.startswith(IGNORE_PREFIXES):
        return True
    if is_dir:
        return name in IGNORE_DIRS
    return (
        name in IGNORE_FILES
        or name.endswith(IGNORE_SUFFIXES)
    )


def build_tree(start: str | os.PathLike = ".", prefix: str = "") -> list[str]:
    start = os.path.realpath(start)
    try:
        entries = sorted(os.listdir(start))
    except PermissionError:
        return []

    result = []
    # filter with is_dir awareness
    filtered = [
        e for e in entries
        if not should_ignore(e, is_dir=os.path.isdir(os.path.join(start, e)))
    ]

    for i, item in enumerate(filtered):
        path = os.path.join(start, item)
        connector = "└── " if i == len(filtered) - 1 else "├── "
        result.append(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if i == len(filtered) - 1 else "│   "
            result.extend(build_tree(path, prefix + extension))

    return result


async def generate_project_description(
    project_root: Path,
    client: AsyncOpenAI,
    model: str = "openai/gpt-4o-mini",
) -> Path:
    output_dir  = project_root / ".cli_agents"
    output_path = output_dir / "PROJECT_DESCRIPTION.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_chunks: list[str] = []

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [
            d for d in dirs
            if not should_ignore(d, is_dir=True)
        ]

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

    tree_lines = build_tree(project_root)
    tree_str   = project_root.name + "/"
    if tree_lines:
        tree_str += "\n" + "\n".join(tree_lines)

    user_message = (
        f"Project tree:\n```\n{tree_str}\n```\n\n"
        "File contents:\n\n"
        + "\n".join(file_chunks)
        + "\n\n---\n"
        "Write a thorough PROJECT_DESCRIPTION.md for this codebase.\n"
        "Cover: purpose, architecture, module breakdown, key classes/functions,\n"
        "data-flow, configuration, and how to run / extend the project.\n"
        "Use clear Markdown with headings, bullet lists, and code snippets."
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior software engineer who writes clear, precise "
                    "technical documentation. Output only valid Markdown."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        max_tokens=4096,
    )

    description_md = response.choices[0].message.content.strip()
    output_path.write_text(description_md, encoding="utf-8")
    return output_path