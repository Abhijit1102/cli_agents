import os
import ast
from pathlib import Path
import seedir as sd
from .ignore import should_ignore, IGNORE_DIRS, IGNORE_FILES

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
