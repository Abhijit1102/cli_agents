import os

IGNORE_NAMES = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    ".next",
    "dist",
    "build",
    ".cache",
    ".idea",
    ".vscode",
}

IGNORE_PREFIXES = (".env",)  # handles .env, .env.local, .env.production


def should_ignore(name: str) -> bool:
    return name in IGNORE_NAMES or name.startswith(IGNORE_PREFIXES)


def build_tree(start: str | os.PathLike = ".", prefix: str = "") -> list[str]:
    # ✅ Resolve to absolute so the tree always reflects the real path
    start = os.path.realpath(start)

    try:
        entries = sorted(os.listdir(start))
    except PermissionError:
        return []

    entries = [e for e in entries if not should_ignore(e)]
    result = []

    for i, item in enumerate(entries):
        path = os.path.join(start, item)
        connector = "└── " if i == len(entries) - 1 else "├── "
        result.append(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if i == len(entries) - 1 else "│   "
            result.extend(build_tree(path, prefix + extension))

    return result