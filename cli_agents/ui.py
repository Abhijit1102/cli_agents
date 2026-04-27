import os
import time
import anyio
from typing import Callable, Awaitable, Optional


from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.align import Align
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich.rule import Rule
from rich.table import Table
from rich import box
from rich.markup import escape

console = Console()

# ── Brand palette (mirrors Claude Code's dark terminal aesthetic) ──────────
ORANGE   = "bold #FF6B35"
ORANGE_D = "#FF6B35"
WHITE    = "bold white"
DIM      = "dim white"
CYAN     = "#5BC8F5"
GREEN    = "bold #3DDC84"
RED      = "bold #FF4F4F"
YELLOW   = "#FFD166"
BG_PANEL = "on #1A1A1A"
BORDER   = "bright_black"

LOGO = r"""
   ___  _     ____     _                    _
  / __\| |   |_ _|    / \   __ _  ___ _ __ | |_ ___
 / /   | |    | |    / _ \ / _` |/ _ \ '_ \| __/ __|
/ /____| |___ | |   / ___ \ (_| |  __/ | | | |_\__ \
\______|_____|___| /_/   \_\__, |\___|_| |_|\__|___/
                           |___/
"""

def _ui_width() -> int:
    width = console.size.width - 6
    return max(60, min(100, width))


def print_logo():
    """Print the branded logo."""
    logo_text = Text(LOGO, style=ORANGE_D, justify="center")
    console.print(logo_text)


def print_version_bar():
    """Print a status bar with version/model info."""
    width = _ui_width()
    left = Text(" cli_agents ", style=f"bold white {BG_PANEL}")
    mid = Text("claude-style terminal assistant", style=f"{DIM} {BG_PANEL}")
    right = Text(" v0.1.0 ", style=f"{DIM} {BG_PANEL}")

    bar = Columns([left, Align.center(mid), Align.right(right)], expand=True)
    console.print(Panel(bar, border_style=BORDER, padding=(0, 1), box=box.HORIZONTALS, width=width, style=BG_PANEL))


def trust_folder_ui():
    """Security trust prompt styled like Claude Code."""
    folder = os.getcwd()

    console.clear()
    console.print()
    print_logo()
    print_version_bar()
    console.print()

    warn = Text("  ⚠  SECURITY CHECK  ⚠", style="bold yellow")
    console.print(Align.center(warn))
    console.print()

    folder_text = Text()
    folder_text.append("  Working directory\n\n", style=DIM)
    folder_text.append(f"  {folder}\n", style=f"bold {CYAN}")
    folder_text.append("\n  Trust this folder to allow file read/write and shell access.", style=DIM)

    console.print(Panel(
        folder_text,
        title=Text("󰉋  Folder Trust", style="bold yellow"),
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 2),
        width=_ui_width(),
    ))

    console.print()
    choice = Prompt.ask(
        "  [bold yellow]Trust this folder?[/bold yellow] [dim]\\[y/n][/dim]",
        choices=["y", "n"],
        default="n",
        show_choices=False,
        show_default=False,
    )

    if choice == "n":
        console.print()
        console.print(Panel(
            Text("  ✖  Aborted. Folder not trusted.", style=RED),
            border_style="red",
            box=box.ROUNDED,
            padding=(0, 1),
            width=_ui_width(),
        ))
        console.print()
        raise SystemExit(0)

    console.print()
    console.print(Panel(
        Text("Folder trusted. Starting agent…", style="white"),
        border_style=GREEN,
        box=box.ROUNDED,
        padding=(0, 1),
        width=_ui_width(),
    ))
    console.print()
    console.print()
    time.sleep(0.4)


def _print_header():
    """Print the session header."""
    width = _ui_width()

    header = Table.grid(expand=True)
    header.add_column(ratio=3)
    header.add_column(ratio=1, justify="right")
    header.add_row(
        Text(" ◆  CLI Agent Session", style="bold white"),
        Text(time.strftime("%H:%M:%S"), style=DIM),
    )

    console.print(Panel(header, border_style=BORDER, box=box.ROUNDED, width=width, padding=(1, 1)))
    console.rule(style="bright_black")

    hints = Text()
    hints.append("  Commands: ", style=DIM)
    hints.append("exit", style=CYAN)
    hints.append(" • ", style=DIM)
    hints.append("/clear", style=CYAN)
    hints.append(" • ", style=DIM)
    hints.append("/help", style=CYAN)
    hints.append(" • ", style=DIM)
    hints.append("/usage", style=CYAN)
    console.print(hints)
    console.print()


def _print_help():
    commands = [
        ("exit / quit", "End the session"),
        ("/clear", "Clear the screen"),
        ("/help", "Show this help"),
        ("/cwd", "Print working directory"),
        ("/usage", "Show token use from last LLM call"),
    ]

    table = Table.grid(padding=(0, 1))
    table.add_column(style=CYAN, ratio=1)
    table.add_column(style=DIM, ratio=2)
    for command, description in commands:
        table.add_row(f"[bold]{command}[/bold]", description)

    console.print(Panel(
        table,
        title=Text(" Commands ", style="bold white"),
        border_style=BORDER,
        box=box.ROUNDED,
        padding=(1, 1),
        width=_ui_width(),
    ))
    console.print()


def _stream_response(text: str):
    """Simulate streaming output character-by-character."""
    prefix = Text(" ◆ ", style=ORANGE_D)
    console.print(prefix, end="")

    delay = max(0.008, min(0.018, 1.0 / max(len(text), 1)))
    for ch in text:
        console.print(ch, end="", style="white", highlight=False)
        time.sleep(delay)
    console.print()
    console.print()


def _spinner_thinking(label: str = "Thinking…"):
    """Return a Live spinner context for the 'thinking' state."""
    spinner_text = Text()
    spinner_text.append(" ◆ ", style=ORANGE_D)
    spinner_text.append(label, style=DIM)
    return Live(
        Spinner("dots", text=spinner_text, style=ORANGE_D),
        console=console,
        refresh_per_second=12,
        transient=True,
    )


def _format_tool_use(tool: str, detail: str = ""):
    """Print a tool-use event like Claude Code does."""
    tool_text = Text()
    tool_text.append("  ⟳ ", style=YELLOW)
    tool_text.append(tool, style=f"bold {YELLOW}")
    if detail:
        tool_text.append(f"  {detail}", style=DIM)

    console.print(Panel(
        tool_text,
        border_style=YELLOW,
        box=box.ROUNDED,
        width=_ui_width(),
        padding=(0, 1),
    ))


async def _stream_from_generator(generator):
    """
    Stream tokens live from an async generator (e.g. OpenAI streaming).
    Shows a spinner until the first token arrives, then prints tokens as they come.
    """
    width = _ui_width()
    content = Text()
    panel = Panel(
        content,
        title=Text(" assistant ", style="bold cyan"),
        border_style=CYAN,
        box=box.ROUNDED,
        width=width,
        padding=(1, 2),
    )

    got_first = False
    with Live(panel, console=console, refresh_per_second=20, transient=False) as live:
        spinner_live = Live(
            Spinner("dots", text=Text(" ◆  Thinking…", style=ORANGE_D), style=ORANGE_D),
            console=console,
            refresh_per_second=12,
            transient=True,
        )
        spinner_live.start()

        try:
            async for token in generator:
                if not got_first:
                    got_first = True
                    spinner_live.stop()
                content.append(token, style="white")
                live.update(Panel(
                    content,
                    title=Text(" assistant ", style="bold cyan"),
                    border_style=CYAN,
                    box=box.ROUNDED,
                    width=width,
                    padding=(1, 2),
                ))
        finally:
            spinner_live.stop()

    if not got_first:
        console.print(Panel(
            Text("No response", style=DIM),
            title=Text(" assistant ", style="bold cyan"),
            border_style=CYAN,
            box=box.ROUNDED,
            width=width,
            padding=(1, 2),
        ))

    console.print()


# ── Public async event loop ────────────────────────────────────────────────

async def event_loop_async(on_message=None, agent=None):
    """
    Async event loop.

    Pass an `on_message` async generator for streaming:
        async def handler(user_input: str):
            async for chunk in openai_stream:
                yield chunk
        await event_loop_async(on_message=handler, agent=agent)

    Without a handler the loop echoes back (useful for UI testing).
    """
    _print_header()
    history: list[str] = []

    while True:
        try:
            # Prompt
            user_input = await anyio.to_thread.run_sync(
                lambda: Prompt.ask(
                    f"\n  [bold {ORANGE_D}]❯[/bold {ORANGE_D}]"
                )
            )
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n\n  [bold red]Session interrupted.[/bold red]\n")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() in ("exit", "quit"):
            console.print(f"\n  [bold {ORANGE_D}]◆[/bold {ORANGE_D}]  [white]Goodbye[/white] [dim]— session ended[/dim]\n")
            break

        if user_input == "/clear":
            console.clear()
            _print_header()
            continue

        if user_input == "/help":
            _print_help()
            continue

        if user_input == "/cwd":
            console.print(f"\n  [dim]cwd[/dim]  [{CYAN}]{escape(os.getcwd())}[/{CYAN}]\n")
            continue

        if user_input == "/usage":
            if agent is None:
                console.print(Panel(
                    Text("Usage is unavailable without an agent.", style=RED),
                    border_style=RED,
                    box=box.ROUNDED,
                    width=_ui_width(),
                    padding=(1, 1),
                ))
                console.print()
                continue

            usage = agent.get_last_usage()
            if not usage:
                usage_text = Text("No token usage recorded yet.", style=DIM)
            else:
                usage_text = Text()
                for key, value in usage.items():
                    usage_text.append(f"{key}: ", style=CYAN)
                    usage_text.append(f"{value}\n", style=WHITE)

            console.print(Panel(
                usage_text,
                title=Text(" Last LLM Usage ", style="bold white"),
                border_style=CYAN,
                box=box.ROUNDED,
                width=_ui_width(),
                padding=(1, 1),
            ))
            console.print()
            continue

        # Echo user bubble
        console.print()
        user_panel = Panel(
            Text(user_input, style="white"),
            border_style=GREEN,
            box=box.ROUNDED,
            padding=(1, 2),
            title=Text(" you ", style="bold green"),
            title_align="left",
            width=_ui_width(),
        )
        console.print(user_panel)
        console.print()

        history.append(user_input)

        # Agent response
        if on_message:
            try:
                await _stream_from_generator(on_message(user_input))
            except Exception as exc:
                console.print(f"  [bold red]✖  Error:[/bold red] [red]{escape(str(exc))}[/red]\n")
                continue
        else:
            # Demo mode — echo with fake latency
            with _spinner_thinking("Processing…"):
                await anyio.sleep(0.6)
            _stream_response(f"(echo) {user_input}")


def event_loop(on_message: Callable[[str], Awaitable[str]] | None = None, agent=None):
    """Sync wrapper so existing code calling event_loop() still works."""
    anyio.run(event_loop_async, on_message, agent)