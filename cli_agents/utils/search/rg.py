import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..fs.ignore import should_ignore


def search_project_rg(
    query: str, root: str | None = None, max_results: int = 25
) -> str:
    """
    High-performance project search.
    Tries ripgrep (rg) first, falls back to a concurrent Python implementation.
    """
    root_path = Path(root or Path.cwd()).resolve()
    if not root_path.exists() or not root_path.is_dir():
        return f"Error: root path not found: {root_path}"

    # 1. Primary: Ripgrep
    rg_binary = shutil.which("rg")
    if rg_binary:
        try:
            return _search_with_rg(rg_binary, query, root_path, max_results)
        except Exception:
            # Fall back to Python instead of crashing if rg fails
            pass

    # 2. Secondary: Concurrent Python Fallback
    return _search_concurrent_python(query, root_path, max_results)


def _search_with_rg(
    rg_binary: str, query: str, root_path: Path, max_results: int
) -> str:
    cmd = [
        rg_binary,
        "--json",
        "--ignore-case",
        "--max-count",
        "2",
        "--max-filesize",
        "1M",
        query,
        str(root_path),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    results = []
    for line in proc.stdout.splitlines():
        try:
            item = json.loads(line)
            if item.get("type") == "match":
                data = item["data"]
                full_path = Path(data["path"]["text"])
                rel_path = (
                    full_path.relative_to(root_path)
                    if full_path.is_absolute()
                    else full_path
                )

                results.append(
                    {
                        "path": str(rel_path),
                        "line_number": data["line_number"],
                        "excerpt": data["lines"]["text"].strip(),
                    }
                )
                if len(results) >= max_results:
                    break
        except (json.JSONDecodeError, KeyError):
            continue

    if not results:
        return f"No matches found for '{query}'."

    return json.dumps(results, indent=2)


def _search_concurrent_python(query: str, root_path: Path, max_results: int) -> str:
    """
    Production-grade Python search using a thread pool and buffered reads.
    """
    query_lower = query.lower()
    files_to_search = []

    # Collect candidate files while respecting ignore rules
    for root, dirs, files in os.walk(root_path):
        # Prune directories in-place to prevent walking into ignored folders
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]

        for file in files:
            if not should_ignore(file, is_dir=False):
                files_to_search.append(Path(root) / file)

    results = []
    # Use ThreadPoolExecutor for I/O bound file reading
    with ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(_search_single_file, f, query_lower, root_path): f
            for f in files_to_search
        }

        for future in as_completed(future_to_file):
            file_matches = future.result()
            if file_matches:
                results.extend(file_matches)

            if len(results) >= max_results:
                break

    # Trim to max_results
    final_results = results[:max_results]
    if not final_results:
        return f"No matches found for '{query}'."

    return json.dumps(final_results, indent=2)


def _search_single_file(
    file_path: Path, query_lower: str, root_path: Path
) -> list[dict[str, Any]]:
    """
    Search a single file using buffered reading to prevent memory spikes.
    """
    matches = []
    try:
        # Open with errors='ignore' to handle mixed encodings/binary files safely
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if query_lower in line.lower():
                    rel_path = file_path.relative_to(root_path)
                    matches.append(
                        {
                            "path": str(rel_path),
                            "line_number": i,
                            "excerpt": line.strip(),
                        }
                    )
                    # Limit matches per file to avoid flooding results
                    if len(matches) >= 2:
                        break
    except (PermissionError, OSError):
        pass  # Skip files that cannot be read

    return matches
