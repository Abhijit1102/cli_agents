"""
diff_renderer.py — Git diff rendering for ChatUI.
"""

import json

from rich import box
from rich.syntax import Syntax
from rich.panel import Panel

from .theme import A, S
from .utils import CONSOLE


def render_git_diff(diff_json: str, console=None, render_system_fn=None) -> None:
    """
    Parses the JSON payload from the git_diff tool and renders
    a colorized, formatted panel to the console.

    Args:
        diff_json:        Raw JSON string from the git_diff tool result.
        console:          Rich Console instance to print to.
        render_system_fn: Optional callable(msg, color) for error/info messages.
                          Falls back to plain console.print if not provided.
    """
    _console = console or CONSOLE

    def _sys(msg: str, color: str = "") -> None:
        if render_system_fn:
            render_system_fn(msg, color)
        else:
            _console.print(f"[{color or 'white'}]{msg}[/]")

    try:
        if not diff_json or not diff_json.strip():
            _sys("Received empty diff payload.", A())
            return

        data = json.loads(diff_json)

        if data.get("error"):
            _sys(f"Diff Tool Error: {data['error']}", A())
            return

        diff_text = data.get("diff", "")
        added     = data.get("added", 0)
        removed   = data.get("removed", 0)

        if not diff_text:
            _sys("No changes detected between versions.", S())
            return

        _console.print(Panel(
            Syntax(
                diff_text,
                "diff",
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            ),
            title=(
                f"[bold cyan]GIT DIFF[/bold cyan] "
                f"[white](+{added} / -{removed})[/white]"
            ),
            title_align="left",
            border_style="cyan",
            padding=(0, 1),
            box=box.ROUNDED,
        ))

    except json.JSONDecodeError:
        _sys(f"Failed to parse Diff JSON. Raw Output:\n{diff_json}", A())
    except Exception as e:
        _sys(f"UI Rendering Error: {str(e)}", A())