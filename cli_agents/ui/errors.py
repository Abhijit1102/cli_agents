from __future__ import annotations

from typing import Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .theme import A, P, W
from .utils import CONSOLE


def _hint_for(error: BaseException) -> str:
    message = str(error).lower()
    if "openai_api_key" in message or "api key" in message:
        return "Add OPENAI_API_KEY to .cli_agents/env.json or set it in the environment."
    if "mcp" in message:
        return "Check .cli_agents/mcp.config.json and confirm the configured server is available."
    if isinstance(error, (FileNotFoundError, NotADirectoryError)):
        return "Check that the project path exists and is accessible."
    if isinstance(error, PermissionError):
        return "Check the file or folder permissions, then try again."
    return "Review the message above, correct the configuration or input, and try again."


def render_error(
    error: BaseException,
    *,
    context: Optional[str] = None,
    console=CONSOLE,
) -> None:
    """Render an exception as a consistent, readable terminal error panel."""
    error_type = type(error).__name__
    message = str(error).strip() or "No additional details were provided."

    details = Table.grid(expand=True, padding=(0, 1))
    details.add_column(style=f"bold {P()}", no_wrap=True)
    details.add_column(ratio=1)
    if context:
        details.add_row("Stage", Text(context, style="bright_white"))
    details.add_row("Type", Text(error_type, style=f"bold {W()}"))
    details.add_row("Message", Text(message, style="bright_white"))
    details.add_row("Next", Text(_hint_for(error), style=f"italic {A()}"))

    console.print(
        Panel(
            details,
            title="[bold red]ERROR[/bold red]",
            subtitle="[dim]cli-agents could not continue[/dim]",
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )
    )