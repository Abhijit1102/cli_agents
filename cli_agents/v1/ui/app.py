"""
app.py — V1 Dual-Process UI Orchestration
"""

import os
import time
from datetime import datetime
from typing import List

import anyio
from rich import box
from rich.live import Live
from rich.status import Status
from rich.text import Text

from cli_agents.config.global_config import get_config
from cli_agents.ui.app import ChatUI
from cli_agents.ui.renderers import AgentStatusRenderer
from cli_agents.ui.diff_renderer import render_git_diff
from cli_agents.ui.errors import render_error
from cli_agents.ui.theme import THEME, P, D, A, S, W
from cli_agents.ui.utils import CONSOLE, local_tz
from cli_agents.ui.slash_commands import ask_with_palette
from cli_agents.v1.ui.v1_ui import V1ChatUI

_DIFF_PREFIX       = "\x00DIFF_RESULT:"
_TOOL_START        = "\x00TOOL_START:"
_MCP_TOOL_START    = "\x00MCP_TOOL_START:"
_TOOL_DONE         = "\x00TOOL_DONE:"
_ERROR_PREFIX      = "\x00ERROR:"


class V1App:
    def __init__(self, agent):
        self.agent = agent
        self.ui = V1ChatUI(agent)
        self.console = CONSOLE
        self.history: List[str] = []

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

    async def _run_with_live_status(self, cmd: str) -> str:
        renderer = AgentStatusRenderer()
        content_parts: List[str] = []
        diff_outputs: List[str] = []
        error_outputs: List[str] = []

        with Live(renderer, console=self.console, refresh_per_second=12, transient=True):
            # Initial status to show System 1 is working
            renderer.set_tool("System 1", "Routing request...", is_mcp=False)
            
            async for chunk in self.agent.handle_message(cmd):
                # ── V1 System Path Markers ──────────────────────────────────
                if chunk.startswith("\x00SYSTEM_PATH:"):
                    # Remove the routing status immediately when the path is decided
                    renderer.set_done() 
                    self.ui._render_assistant(chunk)
                    continue

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
                render_system_fn=self.ui._render_system,
            )

        for error_message in error_outputs:
            render_error(
                RuntimeError(error_message),
                context="Agent execution",
                console=self.console,
            )

        return "".join(content_parts)

    async def run(self) -> None:
        self.console.clear()
        self.ui._render_header()

        with Status(
            "[bold yellow]⚙ Initialising V1 Dual-Process Agent…[/bold yellow]",
            spinner="dots",
            console=self.console,
        ):
            try:
                await self.agent.initialize()
            except Exception as error:
                render_error(error, context="Agent initialization", console=self.console)
                return

        self.ui._render_command_box()

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
                    self.console.clear(); self.ui._render_header(); continue
                if cmd == "/help":
                    self.ui._render_command_box(); continue
                if cmd == "/reset":
                    self.agent.reset(); self.history.clear()
                    self.ui._render_system("Agent memory purged."); continue
                if cmd == "/cwd":
                    self.ui._render_system(f"CWD: {os.getcwd()}", P()); continue
                if cmd == "/usage":
                    self.ui._render_usage(); continue
                if cmd.startswith("/theme"):
                    self.ui._handle_theme(cmd); continue

                self.ui._render_user(cmd)
                self.history.append(cmd)

                try:
                    content = await self._run_with_live_status(cmd)
                    if content.strip():
                        self.ui._render_assistant(content)
                    elif not any(chunk.startswith("\x00SYSTEM_PATH:") for chunk in []): # simplified check
                        # Note: We don't check actual stream here, just if content is empty
                        # but if a SYSTEM_PATH was sent, it's already rendered.
                        pass
                except Exception as e:
                    render_error(e, context="Message execution", console=self.console)

        finally:
            if hasattr(self.agent, "shutdown"):
                with Status(
                    "[bold yellow]⚙ Shutting down V1 Agent…[/bold yellow]",
                    spinner="dots",
                    console=self.console,
                ):
                    await self.agent.shutdown()
