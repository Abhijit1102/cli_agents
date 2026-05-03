import os
import time
import anyio
from typing import List, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich import box

def _make_console() -> Console:
    if os.name == "nt" and os.getenv("MSYSTEM"):
        return Console(force_terminal=True, color_system="auto")
    return Console()

CONSOLE = _make_console()


# ---------------------------
# Security / Trust Prompt
# ---------------------------
def trust_folder_ui() -> None:
    folder = os.getcwd()
    CONSOLE.clear()

    banner = Text("\n⚡ CLI-AGENT TERMINAL ⚡", style="bold white on blue", justify="center")
    CONSOLE.print(Panel(
        banner,
        title="[bold yellow]Security Check[/bold yellow]",
        border_style="bright_blue",
        padding=(1, 2),
        subtitle="[dim]v1.0.0[/dim]"
    ))
    CONSOLE.print(f"  [bold]Current Directory:[/bold] [cyan]{folder}[/cyan]\n")

    answer = Prompt.ask(
        "[bold yellow]?[/bold yellow] Trust this folder and enable file/shell access?",
        choices=["y", "n"], default="n",
    )

    if answer != "y":
        CONSOLE.print(Panel(
            Text("Access Denied. Folder not trusted. Exiting...", style="bold white"),
            title="[bold red]Terminated[/bold red]", border_style="red",
        ))
        raise SystemExit(0)

    CONSOLE.print(Panel(
        Text("Environment Trusted. Initializing Neural Engine...", style="bold green"),
        border_style="green",
    ))
    time.sleep(0.6)


# ---------------------------
# Live Status Renderer
# ---------------------------
class AgentStatusRenderer:
    def __init__(self):
        self.phase: str = "thinking"
        self.tool_name: Optional[str] = None
        self.tool_args: Optional[str] = None
        self.completed_tools: List[str] = []

    def set_thinking(self):
        self.phase = "thinking"
        self.tool_name = None
        self.tool_args = None

    def set_tool(self, name: str, args: str = ""):
        self.phase = "tool"
        self.tool_name = name
        self.tool_args = args

    def add_completed(self, name: str):
        self.completed_tools.append(name)
        self.phase = "thinking"
        self.tool_name = None

    def set_done(self):
        self.phase = "done"

    def __rich__(self):
        rows = []
        for t in self.completed_tools:
            rows.append(Text(f"  ✔  {t}", style="dim green"))

        if self.phase == "thinking":
            spinner = Spinner("dots", text=Text(" agent is thinking…", style="bold cyan"))
            rows.append(spinner)
        elif self.phase == "tool":
            tool_line = Text()
            tool_line.append("  ⚙  executing  ", style="bold bright_yellow")
            tool_line.append(self.tool_name or "?", style="bold white on dark_orange3")
            if self.tool_args:
                tool_line.append(f"  {self.tool_args}", style="dim")
            spinner = Spinner("point", text=tool_line)
            rows.append(spinner)
        elif self.phase == "done":
            rows.append(Text("  ✔  finished", style="bold green"))

        grid = Table.grid(padding=(0, 0))
        grid.add_column()
        for r in rows:
            grid.add_row(r)

        title_color = {"thinking": "cyan", "tool": "bright_yellow", "done": "green"}.get(self.phase, "white")
        return Panel(grid, title=f"[bold {title_color}]AGENT STATUS[/bold {title_color}]", border_style=title_color, box=box.ROUNDED, padding=(0, 1))


# ---------------------------
# Chat UI
# ---------------------------
class ChatUI:
    def __init__(self, agent):
        self.agent = agent
        self.console = CONSOLE
        self.history: List[str] = []

    def _render_header(self) -> None:
        header = Table.grid(expand=True)
        header.add_column(ratio=1)
        header.add_column(justify="right")
        header.add_row(
            Text("🚀 AI CONTROLLER ACTIVE", style="bold magenta"),
            Text("Type [bold white]/help[/bold white] for commands", style="italic dim white"),
        )
        self.console.print(Panel(header, border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 1)))

    def _render_command_box(self) -> None:
        commands = [
            ("/help",    "Show this help menu"),
            ("/reset",   "Wipe short-term memory"),
            ("/usage",   "Check API token consumption"),
            ("/cwd",     "Show current path"),
            ("/history", "Replay user prompts"),
            ("/clear",   "Reset screen view"),
            ("exit",     "Shutdown agent"),
        ]
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Cmd", style="bold cyan")
        table.add_column("Desc", style="italic white")
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        self.console.print(Panel(table, title="[bold cyan]Command Registry[/bold cyan]", border_style="bright_black", padding=(1, 1)))

    def _render_user(self, message: str) -> None:
        self.console.print(Panel(Text(message, style="bright_white"), title="[bold green]USER[/bold green]", title_align="left", border_style="green", box=box.ROUNDED))

    def _render_assistant(self, content: str) -> None:
        markdown = Markdown(content, code_theme="monokai", inline_code_lexer="python")
        self.console.print(Panel(markdown, title="[bold cyan]ASSISTANT[/bold cyan]", title_align="left", border_style="cyan", box=box.ROUNDED))

    def _render_system(self, content: str, color: str = "yellow") -> None:
        now = datetime.now().strftime("%H:%M:%S")
        
        # Comparison Table (The Legend)
        legend = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD)
        legend.add_column("Symbol", style="cyan")
        legend.add_column("Category", style="dim")
        legend.add_column("Vibe", style="italic")
        legend.add_row("⌬ / ⚙", "Techy", "Engine Status")
        legend.add_row("⬢ / ▲", "Geometric", "Visual Anchor")
        legend.add_row("➔ / ≫", "Arrows", "Directional")
        legend.add_row("⌁", "Electric", "Live Connection")

        msg = Text.assemble(
            (f"[{now}] ", "dim"),
            (content, "italic")
        )

        self.console.print(Panel(
            Columns([msg, legend], expand=True),
            title="[bold]SYSTEM LOG[/bold]",
            border_style=color,
            box=box.SQUARE
        ))

    def _render_usage(self) -> None:
        usage = self.agent.get_last_usage() if hasattr(self.agent, "get_last_usage") else None
        if not usage:
            self._render_system("No usage data available.", "red")
            return
        table = Table(title="LLM Token Usage", box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold yellow")
        for k, v in usage.items():
            table.add_row(str(k), str(v))
        self.console.print(table)

    async def _run_with_live_status(self, cmd: str) -> str:
        renderer = AgentStatusRenderer()
        content_parts: List[str] = []
        with Live(renderer, console=self.console, refresh_per_second=12, transient=True):
            async for chunk in self.agent.handle_message(cmd):
                if chunk.startswith("\x00TOOL_START:"):
                    _, rest = chunk.split(":", 1)
                    name, _, args = rest.partition(":")
                    renderer.set_tool(name.strip(), args.strip())
                elif chunk.startswith("\x00TOOL_DONE:"):
                    name = chunk.split(":", 1)[1].strip()
                    renderer.add_completed(name)
                else:
                    content_parts.append(chunk)
            renderer.set_done()
        return "".join(content_parts)

    async def run(self) -> None:
        self.console.clear()
        self._render_header()
        self._render_command_box()

        while True:
            try:
                # CREATIVE MULTI-LINE PROMPT
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                prompt_label = (
                    f"\n[bold bright_black]⧉ System.Ready[/bold bright_black] [dim white][{timestamp}][/dim white]\n"
                    f"[bold green]▲[/bold green] [bold cyan]➥[/bold cyan] "
                )

                user_input = await anyio.to_thread.run_sync(
                    lambda: Prompt.ask(prompt_label)
                )
            except (KeyboardInterrupt, EOFError):
                self.console.print(Text("\nInterrupted. Shutting down...", style="bold red"))
                return

            cmd = user_input.strip()
            if not cmd:
                continue

            if cmd.lower() in {"exit", "quit"}:
                self.console.print(Text("Session Closed. Goodbye!", style="bold blue"))
                break
            
            if cmd == "/clear":
                self.console.clear(); self._render_header(); continue
            if cmd == "/help":
                self._render_command_box(); continue
            if cmd == "/reset":
                self.agent.reset(); self.history.clear()
                self._render_system("Agent memory purged."); continue
            if cmd == "/cwd":
                self._render_system(f"CWD: {os.getcwd()}", "blue"); continue
            if cmd == "/history":
                if not self.history:
                    self._render_system("No history in current session.")
                else:
                    self._render_system("\n".join(f"{i+1}. {m}" for i, m in enumerate(self.history)))
                continue
            if cmd == "/usage":
                self._render_usage(); continue

            self._render_user(cmd)
            self.history.append(cmd)

            try:
                content = await self._run_with_live_status(cmd)
                if content.strip():
                    self._render_assistant(content)
                else:
                    self._render_system("Agent returned an empty response.", "red")
            except Exception as e:
                self._render_system(f"Execution Error: {str(e)}", "red")