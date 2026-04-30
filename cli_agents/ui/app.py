import os
import time
import anyio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from cli_agents.core.agent import AIController


def _make_console() -> Console:
    if os.name == "nt" and os.getenv("MSYSTEM"):
        return Console(force_terminal=True, color_system="auto")
    return Console()


CONSOLE = _make_console()


def trust_folder_ui() -> None:
    folder = os.getcwd()
    CONSOLE.clear()
    banner = Text("CLI-AGENT TERMINAL", style="bold white on blue", justify="center")
    CONSOLE.print(Panel(banner, title="Security Check", border_style="bright_blue", padding=(1, 2)))
    CONSOLE.print(f"Working directory: [bold cyan]{folder}[/bold cyan]\n")
    answer = Prompt.ask("Trust this folder and enable file/shell access?", choices=["y", "n"], default="n")
    if answer != "y":
        CONSOLE.print(Panel(Text("Folder not trusted. Exiting.", style="bold red"), border_style="red"))
        raise SystemExit(0)
    CONSOLE.print(Panel(Text("Folder trusted. Starting agent.", style="bold green"), border_style="green"))
    time.sleep(0.35)


class ChatUI:
    def __init__(self, agent: AIController):
        self.agent = agent
        self.console = CONSOLE
        self.history: list[str] = []

    def _render_header(self) -> None:
        header = Table.grid(expand=True)
        header.add_column(ratio=3)
        header.add_column(justify="right")
        header.add_row(
            Text("🧠 CLI Agent", style="bold white"),
            Text("Type /help for commands", style="dim white"),
        )
        self.console.print(Panel(header, border_style="bright_black", box=box.ROUNDED, padding=(1, 1)))

    def _render_command_box(self) -> None:
        commands = [
            ("/help", "Show built-in commands"),
            ("/reset", "Reset conversation history"),
            ("/usage", "Show last LLM usage"),
            ("/cwd", "Print current working directory"),
            ("/clear", "Clear screen"),
            ("exit", "Exit session"),
        ]
        table = Table.grid(padding=(0, 1))
        table.add_column(style="cyan", ratio=1)
        table.add_column(style="white", ratio=3)
        for command, description in commands:
            table.add_row(f"[bold]{command}[/bold]", description)
        self.console.print(Panel(table, title="Quick Commands", border_style="cyan", box=box.ROUNDED, padding=(1, 1)))

    def _render_user_message(self, message: str) -> None:
        self.console.print(Panel(Text(message, style="white"), title="you", border_style="green", box=box.ROUNDED, padding=(1, 1)))

    def _render_assistant_message(self, content: str) -> None:
        markdown = Markdown(content, code_theme="monokai", hyperlinks=True)
        self.console.print(Panel(markdown, title="assistant", border_style="cyan", box=box.ROUNDED, padding=(1, 1)))

    def _render_plain(self, content: str) -> None:
        self.console.print(Panel(Text(content, style="white"), title="assistant", border_style="cyan", box=box.ROUNDED, padding=(1, 1)))

    def _render_usage(self) -> None:
        usage = self.agent.get_last_usage()
        if not usage:
            self.console.print(Panel(Text("No usage recorded yet."), border_style="yellow", box=box.ROUNDED, padding=(1, 1)))
            return
        rows = "\n".join(f"[cyan]{key}[/cyan]: {value}" for key, value in usage.items())
        self.console.print(Panel(Text(rows, style="white"), title="LLM Usage", border_style="cyan", box=box.ROUNDED, padding=(1, 1)))

    async def run(self) -> None:
        self._render_header()
        self._render_command_box()

        while True:
            try:
                user_input = await anyio.to_thread.run_sync(lambda: Prompt.ask("[bold green]❯[/bold green]"))
            except (KeyboardInterrupt, EOFError):
                self.console.print(Text("\nSession ended.", style="bold red"))
                return

            if not user_input or not user_input.strip():
                continue

            normalized = user_input.strip()
            if normalized.lower() in {"exit", "quit"}:
                self.console.print(Text("Goodbye.", style="bold green"))
                return

            if normalized == "/clear":
                self.console.clear()
                self._render_header()
                self._render_command_box()
                continue

            if normalized == "/help":
                self._render_command_box()
                continue

            if normalized == "/reset":
                message = self.agent.reset()
                self._render_plain(message)
                continue

            if normalized == "/cwd":
                self._render_plain(f"Current working directory: {os.getcwd()}")
                continue

            if normalized == "/usage":
                self._render_usage()
                continue

            self._render_user_message(normalized)
            self.history.append(normalized)

            try:
                content = ""
                async for chunk in self.agent.handle_message(normalized):
                    content += chunk
                if content.strip():
                    self._render_assistant_message(content)
            except Exception as exc:
                self._render_plain(f"Error: {exc}")
