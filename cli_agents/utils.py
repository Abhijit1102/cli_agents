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
    ".vscode"
}

IGNORE_PREFIXES = (".env",)  # handles .env, .env.local, .env.production

def should_ignore(name):
    return (
        name in IGNORE_NAMES
        or name.startswith(IGNORE_PREFIXES)
    )


def build_tree(start=".", prefix=""):
    try:
        entries = sorted(os.listdir(start))
    except PermissionError:
        return []

    result = []

    # filter first (IMPORTANT fix for last-item connector bug)
    entries = [e for e in entries if not should_ignore(e)]

    for i, item in enumerate(entries):
        path = os.path.join(start, item)
        connector = "└── " if i == len(entries) - 1 else "├── "

        result.append(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if i == len(entries) - 1 else "│   "
            result.extend(build_tree(path, prefix + extension))

    return result