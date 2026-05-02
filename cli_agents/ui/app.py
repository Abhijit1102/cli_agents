import os
import time
import anyio
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from cli_agents.core.agent import AIController


# ---------------------------
# Console Setup
# ---------------------------
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

    banner = Text(
        "CLI-AGENT TERMINAL",
        style="bold white on blue",
        justify="center"
    )

    CONSOLE.print(
        Panel(
            banner,
            title="Security Check",
            border_style="bright_blue",
            padding=(1, 2),
        )
    )

    CONSOLE.print(
        f"Working directory: [bold cyan]{folder}[/bold cyan]\n"
    )

    answer = Prompt.ask(
        "Trust this folder and enable file/shell access?",
        choices=["y", "n"],
        default="n",
    )

    if answer != "y":
        CONSOLE.print(
            Panel(
                Text("Folder not trusted. Exiting.", style="bold red"),
                border_style="red",
            )
        )
        raise SystemExit(0)

    CONSOLE.print(
        Panel(
            Text("Folder trusted. Starting agent.", style="bold green"),
            border_style="green",
        )
    )

    time.sleep(0.3)


# ---------------------------
# Chat UI
# ---------------------------
class ChatUI:
    def __init__(self, agent: AIController):
        self.agent = agent
        self.console = CONSOLE
        self.history: List[str] = []

    # -----------------------
    # UI Components
    # -----------------------
    def _render_header(self) -> None:
        header = Table.grid(expand=True)
        header.add_column(ratio=3)
        header.add_column(justify="right")

        header.add_row(
            Text("🧠 CLI Agent", style="bold white"),
            Text("Type /help for commands", style="dim white"),
        )

        self.console.print(
            Panel(
                header,
                border_style="bright_black",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def _render_command_box(self) -> None:
        commands = [
            ("/help", "Show built-in commands"),
            ("/reset", "Reset conversation history"),
            ("/usage", "Show last LLM usage"),
            ("/cwd", "Print current working directory"),
            ("/history", "Show chat history"),
            ("/clear", "Clear screen"),
            ("exit", "Exit session"),
        ]

        table = Table.grid(padding=(0, 1))
        table.add_column(style="cyan", ratio=1)
        table.add_column(style="white", ratio=3)

        for cmd, desc in commands:
            table.add_row(f"[bold]{cmd}[/bold]", desc)

        self.console.print(
            Panel(
                table,
                title="Quick Commands",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def _render_user(self, message: str) -> None:
        self.console.print(
            Panel(
                Text(message, style="white"),
                title="you",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def _render_assistant(self, content: str) -> None:
        markdown = Markdown(
            content,
            code_theme="monokai",
            hyperlinks=True
        )

        self.console.print(
            Panel(
                markdown,
                title="assistant",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def _render_plain(self, content: str) -> None:
        self.console.print(
            Panel(
                Text(content, style="white"),
                title="system",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def _render_usage(self) -> None:
        usage = self.agent.get_last_usage()

        if not usage:
            self._render_plain("No usage recorded yet.")
            return

        rows = "\n".join(
            f"[cyan]{k}[/cyan]: {v}" for k, v in usage.items()
        )

        self.console.print(
            Panel(
                Text(rows),
                title="LLM Usage",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    # -----------------------
    # Main Loop
    # -----------------------
    async def run(self) -> None:
        self._render_header()
        self._render_command_box()

        while True:
            try:
                user_input = await anyio.to_thread.run_sync(
                    lambda: Prompt.ask("[bold green]❯[/bold green]")
                )
            except (KeyboardInterrupt, EOFError):
                self.console.print(Text("\nSession ended.", style="bold red"))
                return

            if not user_input or not user_input.strip():
                continue

            cmd = user_input.strip()

            # -----------------------
            # Exit
            # -----------------------
            if cmd.lower() in {"exit", "quit"}:
                self.console.print(Text("Goodbye.", style="bold green"))
                return

            # -----------------------
            # Commands
            # -----------------------
            if cmd == "/clear":
                self.console.clear()
                self._render_header()
                self._render_command_box()
                continue

            if cmd == "/help":
                self._render_command_box()
                continue

            if cmd == "/reset":
                msg = self.agent.reset()
                self.history.clear()
                self._render_plain(msg)
                continue

            if cmd == "/cwd":
                self._render_plain(f"{os.getcwd()}")
                continue

            if cmd == "/history":
                if not self.history:
                    self._render_plain("No history yet.")
                else:
                    self._render_plain("\n".join(self.history))
                continue

            if cmd == "/usage":
                self._render_usage()
                continue

            # -----------------------
            # Normal Chat
            # -----------------------
            self._render_user(cmd)
            self.history.append(cmd)

            try:
                content = ""

                # Loading indicator
                with self.console.status("[cyan]Thinking..."):
                    async for chunk in self.agent.handle_message(cmd):
                        content += chunk

                if content.strip():
                    self._render_assistant(content)

            except Exception as e:
                self._render_plain(f"Error: {str(e)}")