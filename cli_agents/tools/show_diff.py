import difflib
import json

from cli_agents.config import AppConfig

from .registry import tool


@tool(
    name="git_diff",
    description="Show a git-style diff between two pieces of code or files.",
)
def git_diff(
    config: AppConfig,
    old_code: str = None,
    new_code: str = None,
    file_path: str = None,
) -> str:
    """
    Generates a unified diff and returns it as a JSON string.
    Fix: Prioritizes new_code from arguments over disk content.
    """
    try:
        if old_code is None:
            return json.dumps(
                {
                    "diff": "",
                    "added": 0,
                    "removed": 0,
                    "error": "Missing 'old_code' parameter.",
                }
            )

        if new_code is None:
            return json.dumps(
                {
                    "diff": "",
                    "added": 0,
                    "removed": 0,
                    "error": "Missing 'new_code' parameter. Use this tool to compare changes.",
                }
            )

        from_label = "original"
        to_label = file_path if file_path else "proposed_changes"

        old_lines = old_code.strip().splitlines()
        new_lines = new_code.strip().splitlines()

        diff_gen = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=from_label,
            tofile=to_label,
            lineterm="",
        )

        diff_list = list(diff_gen)

        added = sum(
            1 for l in diff_list if l.startswith("+") and not l.startswith("+++")
        )
        removed = sum(
            1 for l in diff_list if l.startswith("-") and not l.startswith("---")
        )

        return json.dumps(
            {
                "diff": "\n".join(diff_list),
                "added": added,
                "removed": removed,
                "error": None,
            }
        )

    except Exception as e:
        return json.dumps(
            {
                "diff": "",
                "added": 0,
                "removed": 0,
                "error": f"Internal Tool Error: {e!s}",
            }
        )
