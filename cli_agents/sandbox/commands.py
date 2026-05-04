"""
cli_agents/sandbox/commands.py
Slash-command handlers for the sandbox subsystem.

Commands:
    /sandbox create  [--share <path>]
    /sandbox prepare [<id>]
    /sandbox run     [<id>]
    /sandbox attach  [<id>]
    /sandbox exec    [<id>] <command…>
    /sandbox destroy [<id>]
    /sandbox list
    /sandbox status  [<id>]
    /sandbox help
"""
from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .manager import SandboxManager, SandboxSession

if TYPE_CHECKING:
    from cli_agents.ui import ChatUI


# ── helpers ───────────────────────────────────────────────────────────────────

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
    t.add_column("ID",            style="bold cyan",  no_wrap=True)
    t.add_column("Status",        no_wrap=True)
    t.add_column("Created",       style="dim",        no_wrap=True)
    t.add_column("Shared Folder", overflow="fold")
    for s in sessions:
        t.add_row(
            s.id,
            Text(s.status, style=_status_color(s.status)),
            s.created_at[:19].replace("T", " "),
            str(s.shared_folder) if s.shared_folder else "—",
        )
    return t


# ── dispatcher ────────────────────────────────────────────────────────────────

def handle_sandbox_command(ui: "ChatUI", raw: str) -> None:
    try:
        tokens = shlex.split(raw.strip())
    except ValueError as exc:
        ui._render_system(f"Parse error: {exc}", "red")
        return

    if not tokens:
        _cmd_help(ui)
        return

    sub  = tokens[0].lower()
    args = tokens[1:]

    manager = SandboxManager(ui.agent.config.project_root)

    dispatch = {
        "create":  _cmd_create,
        "prepare": _cmd_prepare,
        "run":     _cmd_run,
        "attach":  _cmd_attach,
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


# ── sub-commands ──────────────────────────────────────────────────────────────

def _cmd_help(ui: "ChatUI") -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Cmd",  style="bold cyan")
    t.add_column("Args", style="dim")
    t.add_column("Desc")
    rows = [
        ("/sandbox create",  "[--share <path>]",  "Build .wsb config + register session"),
        ("/sandbox prepare", "[<id>]",             "Copy bootstrap + package into share"),
        ("/sandbox run",     "[<id>]",             "Launch Windows Sandbox"),
        ("/sandbox attach",  "[<id>]",             "Open interactive prompt inside sandbox"),
        ("/sandbox exec",    "[<id>] <cmd…>",      "Run one shell command inside sandbox"),
        ("/sandbox destroy", "[<id>]",             "Kill + clean up sandbox"),
        ("/sandbox list",    "",                   "Show all sessions"),
        ("/sandbox status",  "[<id>]",             "Show detail for one session"),
    ]
    for cmd, arg, desc in rows:
        t.add_row(cmd, arg, desc)
    ui.console.print(Panel(
        t,
        title="[bold cyan]Sandbox Commands[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))


def _cmd_create(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
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

    if shared is None:
        shared = manager.project_root
        ui._render_system(
            f"No --share given; defaulting to project root: {shared}", "yellow"
        )

    session = manager.create(shared_folder=shared)
    ui._render_system(
        f"Sandbox created  id=[bold cyan]{session.id}[/bold cyan]  wsb={session.wsb_path}",
        "green",
    )
    ui._render_system(
        f"Run [bold]/sandbox prepare {session.id}[/bold] next to copy files into the share.",
        "yellow",
    )


def _cmd_prepare(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox prepare [<id>]
    Copies bootstrap.ps1 + cli_agents package into the shared folder.
    Must be done before /sandbox run so the sandbox can self-install.
    """
    sid = args[0] if args else None
    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions. Run /sandbox create first.", "red")
            return
        sid = session.id
        ui._render_system(f"No id given; preparing latest session: {sid}", "yellow")

    ui._render_system(f"Preparing share for sandbox [{sid}] …", "cyan")
    ok, msg = manager.prepare_share(sid)
    color   = "green" if ok else "red"
    ui._render_system(f"{'✅' if ok else '❌'} {msg}", color)


def _cmd_run(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    sid = args[0] if args else None
    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions. Run /sandbox create first.", "red")
            return
        sid = session.id
        ui._render_system(f"No id given; using latest session: {sid}", "yellow")

    ok, msg = manager.run(sid)
    ui._render_system(f"{'✅' if ok else '❌'} {msg}", "green" if ok else "red")
    if ok:
        ui._render_system(
            "Sandbox is booting. Run [bold]/sandbox attach[/bold] to connect "
            "(waits up to 120 s for the agent to be ready).",
            "yellow",
        )


def _cmd_attach(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    """
    /sandbox attach [<id>]
    Blocks until sandbox bridge is ready, then opens an interactive REPL
    that forwards every prompt to the agent running inside the sandbox.
    Type 'exit' or press Ctrl-C to return to the host CLI.
    """
    from .bridge_host import BridgeTimeout

    try:
        from prompt_toolkit import prompt as pt_prompt
    except ImportError:
        pt_prompt = None  # fall back to input()

    sid = args[0] if args else None
    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system(
                "No sessions. Run /sandbox create → prepare → run first.", "red"
            )
            return
        sid = session.id

    ui._render_system(
        f"Waiting for sandbox [{sid}] to be ready (up to 120 s) …", "yellow"
    )

    try:
        bridge = manager.attach(sid)
    except BridgeTimeout as exc:
        ui._render_system(str(exc), "red")
        return
    except Exception as exc:
        ui._render_system(f"Attach failed: {exc}", "red")
        return

    ui._render_system(
        f"[bold green]Connected to sandbox [{sid}][/bold green]  "
        "Type [bold]exit[/bold] or Ctrl-C to return to host.",
        "green",
    )

    while True:
        try:
            if pt_prompt is not None:
                user_input = pt_prompt("sandbox> ").strip()
            else:
                user_input = input("sandbox> ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "/exit"}:
            break

        ui._render_system(f"→ [{sid}]: {user_input}", "cyan")
        try:
            response = bridge.send(user_input, timeout=120.0)
            if response.strip():
                ui._render_assistant(response)
            else:
                ui._render_system("(sandbox agent returned empty response)", "yellow")
        except BridgeTimeout:
            ui._render_system(
                "Timed out waiting for sandbox response. "
                "The agent may still be running — try again or /sandbox destroy.",
                "red",
            )
        except Exception as exc:
            ui._render_system(f"Bridge error: {exc}", "red")

    ui._render_system(f"Detached from sandbox [{sid}]. Back on host.", "yellow")


def _cmd_exec(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    if not args:
        ui._render_system("Usage: /sandbox exec [<id>] <command…>", "red")
        return

    sessions  = manager.list_sessions()
    known_ids = {s.id for s in sessions}

    if args[0] in known_ids:
        sid     = args[0]
        command = " ".join(args[1:])
    else:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions. Run /sandbox create first.", "red")
            return
        sid     = session.id
        command = " ".join(args)

    if not command.strip():
        ui._render_system("No command provided.", "red")
        return

    ui._render_system(f"Executing in sandbox [{sid}]: {command}", "cyan")
    ok, output = manager.exec(sid, command)
    ui.console.print(Panel(
        Syntax(output or "(no output)", "powershell", theme="monokai", word_wrap=True),
        title=f"[{'green' if ok else 'red'}]{'✅ Success' if ok else '❌ Failed'}[/] — {sid}",
        border_style="green" if ok else "red",
        box=box.ROUNDED,
    ))


def _cmd_destroy(ui: "ChatUI", manager: SandboxManager, args: list[str]) -> None:
    sid = args[0] if args else None
    if sid is None:
        session = manager.latest_session()
        if session is None:
            ui._render_system("No sessions.", "red")
            return
        sid = session.id
        ui._render_system(f"No id given; destroying latest: {sid}", "yellow")

    ok, msg = manager.destroy(sid)
    ui._render_system(f"{'🗑' if ok else '❌'} {msg}", "green" if ok else "red")


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
            ui._render_system("No sessions.", "red")
            return
        sid = session.id

    session = manager.get_session(sid)
    if session is None:
        ui._render_system(f"No sandbox with id '{sid}'.", "red")
        return

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