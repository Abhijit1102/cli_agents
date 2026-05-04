"""
cli_agents/sandbox/commands.py

Slash-command handlers for the sandbox subsystem.
Registered commands:
    /sandbox create  [--share <path>]
    /sandbox run     [<id>]
    /sandbox exec    [<id>] <command…>
    /sandbox destroy [<id>]
    /sandbox list
    /sandbox status  [<id>]

Each handler receives the ChatUI instance so it can call _render_* helpers
for consistent visual output.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from rich.table import Table
from rich.text import Text
from rich import box

from .manager import SandboxManager, SandboxSession

if TYPE_CHECKING:
    from cli_agents.ui import ChatUI


# ─── helpers ──────────────────────────────────────────────────────────────────

def _status_color(status: str) -> str:
    return {
        "created":   "yellow",
        "running":   "bright_green",
        "stopped":   "dim white",
        "destroyed": "red",
    }.get(status, "white")


def _session_table(sessions: list[SandboxSession]) -> Table:
    t = Table(
        title="Sandbox Sessions",
        box=box.MINIMAL_DOUBLE_HEAD,
        show_lines=False,
    )
    t.add_column("ID",         style="bold cyan",   no_wrap=True)
    t.add_column("Status",     no_wrap=True)
    t.add_column("Created",    style="dim",          no_wrap=True)
    t.add_column("Shared Folder", overflow="fold")

    for s in sessions:
        t.add_row(
            s.id,
            Text(s.status, style=_status_color(s.status)),
            s.created_at[:19].replace("T", " "),
            str(s.shared_folder) if s.shared_folder else "—",
        )
    return t


# ─── command dispatcher ───────────────────────────────────────────────────────

def handle_sandbox_command(ui: "ChatUI", raw: str) -> None:
    """
    Entry point called from ChatUI.run() when the user types /sandbox …
    `raw` is everything AFTER the /sandbox prefix, e.g. "create --share ."
    """
    try:
        tokens = shlex.split(raw.strip())
    except ValueError as exc:
        ui._render_system(f"Parse error: {exc}", "red")
        return

    if not tokens:
        _cmd_help(ui)
        return

    sub = tokens[0].lower()
    args = tokens[1:]

    manager = SandboxManager(ui.agent.config.project_root)

    dispatch = {
        "create":  _cmd_create,
        "run":     _cmd_run,
        "exec":    _cmd_exec,
        "destroy": _cmd_destroy,
        "list":    _cmd_list,
        "status":  _cmd_status,
        "help":    lambda u, m, a: _cmd_help(u),
    }

    fn = dispatch.get(sub)
    if fn is None:
        ui._render_system(
            f"Unknown sub-command '{sub}'. Try /sandbox help.", "red"
        )
        return

    fn(ui, manager, args)


# ─── sub-commands ─────────────────────────────────────────────────────────────

def _cmd_help(ui: "ChatUI") -> None:
    from rich.table import Table
    from rich import box

    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Cmd",  style="bold cyan")
    t.add_column("Args", style="dim")
    t.add_column("Desc")

    rows = [
        ("/sandbox create",  "[--share <path>]",     "Build a .wsb config + register session"),
        ("/sandbox run",     "[<id>]",                "Launch WindowsSandbox for a session"),
        ("/sandbox exec",    "[<id>] <cmd…>",         "Run a command inside the sandbox"),
        ("/sandbox destroy", "[<id>]",                "Kill & clean up a sandbox"),
        ("/sandbox list",    "",                      "Show all sessions"),
        ("/sandbox status",  "[<id>]",                "Show detail for one session"),
    ]
    for cmd, args, desc in rows:
        t.add_row(cmd, args, desc)

    from rich.panel import Panel
    ui.console.print(Panel(
        t,
        title="[bold cyan]Sandbox Commands[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))


def _cmd_create(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox create [--share <path>]
    """
    shared: Path | None = None

    i = 0
    while i < len(args):
        if args[i] in {"--share", "-s"} and i + 1 < len(args):
            shared = Path(args[i + 1]).resolve()
            if not shared.exists():
                ui._render_system(f"Shared folder not found: {shared}", "red")
                return
            i += 2
        else:
            i += 1

    # Default share = project root
    if shared is None:
        shared = manager.project_root
        ui._render_system(
            f"No --share given; defaulting to project root: {shared}", "yellow"
        )

    session = manager.create(shared_folder=shared)
    ui._render_system(
        f"✅ Sandbox created  id=[bold cyan]{session.id}[/bold cyan]  "
        f"wsb={session.wsb_path}",
        "green",
    )


def _cmd_run(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox run [<id>]   — omit id to use the latest session
    """
    sid = args[0] if args else None

    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions found. Run /sandbox create first.", "red")
            return
        sid = session.id
        ui._render_system(f"No id given; using latest session: {sid}", "yellow")

    ok, msg = manager.run(sid)
    color = "green" if ok else "red"
    ui._render_system(f"{'✅' if ok else '❌'} {msg}", color)


def _cmd_exec(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox exec [<id>] <command…>

    If the first token looks like a known session id (8-char hex), treat it
    as the id and the rest as the command; otherwise use the latest session.
    """
    if not args:
        ui._render_system("Usage: /sandbox exec [<id>] <command…>", "red")
        return

    # Heuristic: 8-char hex = session id
    sessions = manager.list_sessions()
    known_ids = {s.id for s in sessions}

    if args[0] in known_ids:
        sid = args[0]
        command = " ".join(args[1:])
    else:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions found. Run /sandbox create first.", "red")
            return
        sid = session.id
        command = " ".join(args)

    if not command.strip():
        ui._render_system("No command provided.", "red")
        return

    ui._render_system(f"⚙ Executing in sandbox [{sid}]: {command}", "cyan")
    ok, output = manager.exec(sid, command)

    from rich.syntax import Syntax
    from rich.panel import Panel

    panel = Panel(
        Syntax(output or "(no output)", "powershell", theme="monokai", word_wrap=True),
        title=f"[{'green' if ok else 'red'}]{'✅ Success' if ok else '❌ Failed'}[/] — sandbox {sid}",
        border_style="green" if ok else "red",
        box=box.ROUNDED,
    )
    ui.console.print(panel)


def _cmd_destroy(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox destroy [<id>]   — omit id to destroy the latest session
    """
    sid = args[0] if args else None

    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions found.", "red")
            return
        sid = session.id
        ui._render_system(f"No id given; destroying latest session: {sid}", "yellow")

    ok, msg = manager.destroy(sid)
    color = "green" if ok else "red"
    ui._render_system(f"{'🗑' if ok else '❌'} {msg}", color)


def _cmd_list(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    sessions = manager.list_sessions()
    if not sessions:
        ui._render_system("No sandbox sessions found.", "yellow")
        return
    ui.console.print(_session_table(sessions))


def _cmd_status(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    sid = args[0] if args else None

    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions found.", "red")
            return
        sid = session.id

    session = manager.get_session(sid)
    if session is None:
        ui._render_system(f"No sandbox with id '{sid}'.", "red")
        return

    from rich.table import Table
    from rich.panel import Panel

    t = Table(show_header=False, box=box.SIMPLE)
    t.add_column("Key",   style="bold cyan")
    t.add_column("Value")

    for k, v in session.to_dict().items():
        t.add_row(k, Text(str(v), style=_status_color(v) if k == "status" else ""))

    ui.console.print(Panel(
        t,
        title=f"[bold cyan]Sandbox {sid}[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))