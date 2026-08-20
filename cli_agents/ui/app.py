"""
app.py — ChatUI (orchestration layer)
"""

import os
import time
from datetime import datetime
from typing import List

import anyio
from rich import box
from rich.columns import Columns
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.status import Status

from cli_agents.config.global_config import get_config
from .clock import animated_timestamp, LiveClock, render_theme_preview
from .renderers import AgentStatusRenderer
from .diff_renderer import render_git_diff
from .errors import render_error
from cli_agents.utils import generate_project_description
from .theme import THEME, P, D, A, S, W
from .utils import CONSOLE, local_tz
from .slash_commands import ask_with_palette

_DIFF_PREFIX       = "\x00DIFF_RESULT:"
_TOOL_START        = "\x00TOOL_START:"
_MCP_TOOL_START    = "\x00MCP_TOOL_START:"
_TOOL_DONE         = "\x00TOOL_DONE:"
_ERROR_PREFIX      = "\x00ERROR:"


class ChatUI:
    def __init__(self, agent):
        self.agent   = agent
        self.console = CONSOLE
        self.history: List[str] = []

    # ── shared helpers ────────────────────────────────────────────────────────
    def _ts_row(self, label: str) -> Table:
        h = Table.grid(expand=True)
        h.add_column(ratio=1); h.add_column(justify="right")
        h.add_row(Text(label, style=f"bold {P()}"), animated_timestamp())
        return h

    def _body(self, *rows) -> Table:
        t = Table.grid(); t.add_column()
        for r in rows:
            t.add_row(r)
        return t

    # ── renders ───────────────────────────────────────────────────────────────
    def _render_header(self) -> None:
        left  = Text.assemble(("🚀 AI CONTROLLER ACTIVE", f"bold {P()}"))
        right = Text.assemble(
            ("Type ",         f"dim {D()}"),
            ("/help",         f"bold {P()}"),
            (" for commands", f"italic dim {D()}"),
        )
        header = Table.grid(expand=True)
        header.add_column(ratio=1); header.add_column(justify="right")
        header.add_row(left, right)
        self.console.print(Panel(
            header, border_style=P(), box=box.DOUBLE_EDGE, padding=(0, 1),
        ))

    def _render_command_box(self) -> None:
        commands = [
            ("/help",         "Show this help menu"),
            ("/reset",        "Wipe short-term memory"),
            ("/usage",        "Check API token consumption"),
            ("/cwd",          "Show current path"),
            ("/history",      "Replay user prompts"),
            ("/clear",        "Reset screen view"),
            ("/clock",        "Show live system clock"),
            ("/theme",        "List themes"),
            ("/theme <name>", "Switch active theme instantly"),
            ("exit",          "Shutdown agent"),
        ]
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Cmd",  style=f"bold {P()}")
        table.add_column("Desc", style=f"italic {D()}")
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        self.console.print(Panel(
            table,
            title=f"[bold {P()}]Command Registry[/bold {P()}]",
            border_style=A(), padding=(1, 1),
        ))

    def _render_user(self, message: str) -> None:
        self.console.print(Panel(
            self._body(
                self._ts_row("USER"),
                Text(f"\n{message}\n", style="bright_white"),
            ),
            title=f"[bold {S()}]USER[/bold {S()}]",
            title_align="left", border_style=S(), box=box.ROUNDED,
        ))

    def _render_assistant(self, content: str) -> None:
        self.console.print(Panel(
            self._body(
                self._ts_row("ASSISTANT"),
                Markdown(content, code_theme="monokai", inline_code_lexer="python"),
            ),
            title=f"[bold {P()}]ASSISTANT[/bold {P()}]",
            title_align="left", border_style=P(), box=box.ROUNDED,
        ))

    def _render_system(self, content: str, color: str = "") -> None:
        c   = color or W()
        now = datetime.now(local_tz).strftime("%H:%M:%S")

        legend = Table(show_header=True, header_style=f"bold {A()}", box=box.SIMPLE_HEAD)
        legend.add_column("Symbol",   style=f"{P()}")
        legend.add_column("Category", style="dim")
        legend.add_column("Vibe",     style="italic")
        legend.add_row("⌬ / ⚙", "Techy",     "Engine Status")
        legend.add_row("⬢ / ▲", "Geometric", "Visual Anchor")
        legend.add_row("➔ / ≫", "Arrows",    "Directional")
        legend.add_row("⌁",     "Electric",  "Live Connection")

        msg = Text.assemble(
            (f"[{now}] ", f"dim {D()}"),
            (content,     f"italic {c}"),
        )
        self.console.print(Panel(
            Columns([msg, legend], expand=True),
            title="[bold]SYSTEM LOG[/bold]",
            border_style=c, box=box.SQUARE,
        ))

    def _render_usage(self) -> None:
        usage = self.agent.get_last_usage() if hasattr(self.agent, "get_last_usage") else None
        if not usage:
            self._render_system("No usage data available.", A())
            return
        table = Table(title="LLM Token Usage", box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Metric", style=f"{P()}")
        table.add_column("Value",  style=f"bold {W()}")
        for k, v in usage.items():
            table.add_row(str(k), str(v))
        self.console.print(table)

    def _render_live_clock(self, duration: float = 5.0) -> None:
        with Live(LiveClock(), console=self.console, refresh_per_second=10, transient=True):
            time.sleep(duration)

    def _render_mcp_servers(self) -> None:
        """Show which MCP servers are currently connected."""
        mcp = getattr(self.agent, "mcp", None)
        if not mcp or not mcp.sessions:
            self._render_system("No MCP servers connected.", A())
            return
        table = Table(
            title="Connected MCP Servers",
            box=box.MINIMAL_DOUBLE_HEAD,
            header_style=f"bold {A()}",
        )
        table.add_column("Server", style=f"bold {A()}")
        table.add_column("Status", style=f"{S()}")
        for name in mcp.sessions:
            table.add_row(name, "🟢 connected")
        self.console.print(table)

    # ── /theme handler ────────────────────────────────────────────────────────
    def _handle_theme(self, cmd: str) -> None:
        parts = cmd.strip().split()
        if len(parts) == 1:
            render_theme_preview(self.console)
            return
        name = parts[1].lower()
        if not THEME.set_theme(name):
            self._render_system(
                f"Unknown theme '{name}'.  Available: {', '.join(THEME.list_themes())}", A()
            )
            return
        self.console.clear()
        self._render_header()
        self._render_system(f"Theme changed to: {name}", S())

    # ── prompt label ──────────────────────────────────────────────────────────
    def _get_prompt_label(self) -> str:
        user = os.getenv("USERNAME") or os.getenv("USER") or "user"
        host = os.uname().nodename if hasattr(os, "uname") else "localhost"
        cwd  = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        return (
            f"[bold {S()}]{user}@{host}[/bold {S()}]:"
            f"[bold {P()}]{cwd}[/bold {P()}]$ "
        )

    # ── agent runner ──────────────────────────────────────────────────────────
    async def _run_with_live_status(self, cmd: str) -> str:
        renderer = AgentStatusRenderer()
        content_parts: List[str] = []
        diff_outputs: List[str] = []
        error_outputs: List[str] = []

        with Live(renderer, console=self.console, refresh_per_second=12, transient=True):
            async for chunk in self.agent.handle_message(cmd):

                # ── MCP tool starting ────────────────────────────────────────
                if chunk.startswith(_MCP_TOOL_START):
                    _, rest = chunk.split(":", 1)
                    name, _, args = rest.partition(":")
                    renderer.set_tool(name.strip(), args.strip(), is_mcp=True)

                # ── local tool starting ──────────────────────────────────────
                elif chunk.startswith(_TOOL_START):
                    _, rest = chunk.split(":", 1)
                    name, _, args = rest.partition(":")
                    renderer.set_tool(name.strip(), args.strip(), is_mcp=False)

                # ── tool finished ────────────────────────────────────────────
                elif chunk.startswith(_TOOL_DONE):
                    renderer.add_completed(chunk.split(":", 1)[1].strip())

                # ── git diff payload ─────────────────────────────────────────
                elif chunk.startswith(_DIFF_PREFIX):
                    diff_outputs.append(chunk[len(_DIFF_PREFIX):])

                # ── formatted error payload ───────────────────────────────
                elif chunk.startswith(_ERROR_PREFIX):
                    error_outputs.append(chunk[len(_ERROR_PREFIX):].strip())

                # ── regular prose ────────────────────────────────────────────
                else:
                    content_parts.append(chunk)

            renderer.set_done()

        for diff_json in diff_outputs:
            render_git_diff(
                diff_json,
                console=self.console,
                render_system_fn=self._render_system,
            )

        for error_message in error_outputs:
            render_error(
                RuntimeError(error_message),
                context="Agent execution",
                console=self.console,
            )

        return "".join(content_parts)

    # ── main loop ─────────────────────────────────────────────────────────────
    async def run(self) -> None:
        self.console.clear()
        self._render_header()

        # ── initialise agent (loads MCP servers if configured) ────────────────
        with Status(
            "[bold yellow]⚙ Initialising agent…[/bold yellow]",
            spinner="dots",
            console=self.console,
        ):
            try:
                await self.agent.initialize()
            except Exception as error:
                render_error(error, context="Agent initialization", console=self.console)
                return

        # Show MCP status after init
        mcp = getattr(self.agent, "mcp", None)
        if mcp and mcp.sessions:
            self._render_mcp_servers()
        
        self._render_command_box()

        try:
            while True:
                try:
                    user_input = await anyio.to_thread.run_sync(
                        lambda: ask_with_palette(self._get_prompt_label())
                    )
                except (KeyboardInterrupt, EOFError):
                    self.console.print(Text("\nInterrupted. Shutting down...", style=f"bold {A()}"))
                    break

                cmd = user_input.strip()
                if not cmd:
                    continue

                if cmd.lower() in {"exit", "quit"}:
                    self.console.print(Text("Session Closed. Goodbye!", style=f"bold {P()}"))
                    break

                if cmd == "/clear":
                    self.console.clear(); self._render_header(); continue
                if cmd == "/help":
                    self._render_command_box(); continue
                if cmd == "/reset":
                    self.agent.reset(); self.history.clear()
                    self._render_system("Agent memory purged."); continue
                if cmd == "/cwd":
                    self._render_system(f"CWD: {os.getcwd()}", P()); continue
                if cmd == "/mcp":
                    self._render_mcp_servers(); continue
                if cmd == "/history":
                    if not self.history:
                        self._render_system("No history in current session.")
                    else:
                        self._render_system(
                            "\n".join(f"{i+1}. {m}" for i, m in enumerate(self.history))
                        )
                    continue
                if cmd == "/usage":
                    self._render_usage(); continue
                if cmd == "/clock":
                    self._render_live_clock(5.0); continue
                if cmd.startswith("/theme"):
                    self._handle_theme(cmd); continue
                if cmd.startswith("/sandbox"):
                    suffix = cmd[len("/sandbox"):].strip()
                    handle_sandbox_command(self, suffix)
                    continue
                if cmd == "/config":
                    cfg = self.agent.config
                    msg = (
                        f"Model:    {cfg.model}\n"
                        f"Base URL: {cfg.openai_base_url or 'default'}\n"
                        f"MCP:      {str(cfg.mcp_config_path) if cfg.mcp_config_path else 'not configured'}"
                    )
                    self._render_system(msg.strip(), P())
                    continue

                if cmd == "/init_project":
                    cfg = self.agent.config
                    with Status(
                        "[bold yellow]⚙ Scanning project • analysing • generating description…[/bold yellow]",
                        spinner="dots",
                        console=self.console,
                    ):
                        try:
                            path = await generate_project_description(
                                project_root=cfg.project_root,
                                client=self.agent.client,
                                model=cfg.model,
                            )
                        except Exception as e:
                            render_error(e, context="Project initialization", console=self.console)
                            continue

                    self._render_system(f"✅ PROJECT_DESCRIPTION.md written → {path}", S())
                    continue

                self._render_user(cmd)
                self.history.append(cmd)

                try:
                    content = await self._run_with_live_status(cmd)
                    if content.strip():
                        self._render_assistant(content)
                    else:
                        self._render_system("Agent returned an empty response.", A())
                except Exception as e:
                    render_error(e, context="Message execution", console=self.console)

        finally:
            # ── always clean up MCP servers on exit ───────────────────────────
            if hasattr(self.agent, "shutdown"):
                with Status(
                    "[bold yellow]⚙ Shutting down MCP servers…[/bold yellow]",
                    spinner="dots",
                    console=self.console,
                ):
                    await self.agent.shutdown()