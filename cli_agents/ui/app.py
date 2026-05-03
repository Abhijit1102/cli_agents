import os
import time
import anyio
import threading
from typing import List, Optional
from datetime import datetime
import zoneinfo

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich.align import Align
from rich import box

def _make_console() -> Console:
    if os.name == "nt" and os.getenv("MSYSTEM"):
        return Console(force_terminal=True, color_system="truecolor")
    return Console(color_system="truecolor")

CONSOLE  = _make_console()
local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")


# ──────────────────────────────────────────────
# THEME SYSTEM
# ──────────────────────────────────────────────
class ThemeManager:
    THEMES = {
        "cyan":   {"primary": "#00f5ff", "dim": "#007a80", "accent": "#bf5fff", "success": "#39ff14", "warn": "#ffe600"},
        "green":  {"primary": "#39ff14", "dim": "#145c14", "accent": "#00f5ff", "success": "#ffe600", "warn": "#ff6b35"},
        "purple": {"primary": "#bf5fff", "dim": "#4b1f73", "accent": "#ff2079", "success": "#39ff14", "warn": "#ffe600"},
        "yellow": {"primary": "#ffe600", "dim": "#7a6f00", "accent": "#ff6b35", "success": "#39ff14", "warn": "#ff2079"},
        "orange": {"primary": "#ff6b35", "dim": "#7a2f14", "accent": "#ffe600", "success": "#39ff14", "warn": "#ff2079"},
        "pink":   {"primary": "#ff2079", "dim": "#7a0033", "accent": "#bf5fff", "success": "#39ff14", "warn": "#ffe600"},
        "white":  {"primary": "#ffffff", "dim": "#aaaaaa", "accent": "#00f5ff", "success": "#39ff14", "warn": "#ffe600"},
    }

    SHIFT_FRAMES = {
        "cyan":   ["#00f5ff", "#bf5fff", "#39ff14", "#ffe600", "#ff2079", "#ff6b35"],
        "green":  ["#39ff14", "#00f5ff", "#ffe600", "#bf5fff", "#ff6b35", "#39ff14"],
        "purple": ["#bf5fff", "#ff2079", "#00f5ff", "#ffe600", "#39ff14", "#bf5fff"],
        "yellow": ["#ffe600", "#ff6b35", "#ff2079", "#00f5ff", "#bf5fff", "#39ff14"],
        "orange": ["#ff6b35", "#ffe600", "#ff2079", "#bf5fff", "#00f5ff", "#39ff14"],
        "pink":   ["#ff2079", "#bf5fff", "#ffe600", "#ff6b35", "#00f5ff", "#39ff14"],
        "white":  ["#ffffff", "#aaaaaa", "#00f5ff", "#bf5fff", "#ffe600", "#39ff14"],
    }

    def __init__(self):
        self._frame = 0
        self._lock  = threading.Lock()
        self.set_theme("cyan")

    def set_theme(self, name: str) -> bool:
        t = self.THEMES.get(name.lower())
        if not t:
            return False
        self.name    = name.lower()
        self.primary = t["primary"]
        self.dim     = t["dim"]
        self.accent  = t["accent"]
        self.success = t["success"]
        self.warn    = t["warn"]
        with self._lock:
            self._frame = 0
        return True

    def next_shift(self) -> str:
        frames = self.SHIFT_FRAMES[self.name]
        with self._lock:
            c = frames[self._frame % len(frames)]
            self._frame += 1
        return c

    def list_themes(self) -> list:
        return list(self.THEMES.keys())


THEME = ThemeManager()

# Helpers — always resolved at call time so a /theme switch is instant
def P()  -> str: return THEME.primary
def D()  -> str: return THEME.dim
def A()  -> str: return THEME.accent
def S()  -> str: return THEME.success
def W()  -> str: return THEME.warn
def SH() -> str: return THEME.next_shift()


# ──────────────────────────────────────────────
# ANIMATED TIMESTAMP
# ──────────────────────────────────────────────
def _animated_timestamp() -> Text:
    now   = datetime.now(local_tz)
    color = SH()
    t = Text()
    t.append("◈ ",                     style=f"bold {A()}")
    t.append(now.strftime("%Y-%m-%d"), style=f"dim {P()}")
    t.append("  ⏱ ",                  style=f"bold {color}")
    t.append(now.strftime("%H:%M:%S"), style=f"bold {color} blink")
    t.append(" ◈",                     style=f"bold {A()}")
    return t


# ──────────────────────────────────────────────
# LIVE CLOCK
# ──────────────────────────────────────────────
class LiveClock:
    def __rich__(self) -> Panel:
        now   = datetime.now(local_tz)
        color = SH()
        t = Text(justify="center")
        t.append("\n")
        t.append(now.strftime("%H:%M:%S"),              style=f"bold {color}")
        t.append(f".{now.strftime('%f')[:3]}",           style=f"dim {D()}")
        t.append(f"\n{now.strftime('%A, %d %B %Y')}\n", style=f"dim {A()}")
        return Panel(
            Align.center(t),
            title=f"[bold {P()}]◈ SYSTEM CLOCK ◈[/bold {P()}]",
            border_style=P(), box=box.DOUBLE_EDGE, padding=(0, 2),
        )


# ──────────────────────────────────────────────
# THEME SWATCH PREVIEW
# ──────────────────────────────────────────────
def _render_theme_preview(console: Console) -> None:
    header = Text.assemble(
        ("◈ AVAILABLE THEMES ◈\n",             f"bold {P()}"),
        (f"  current → {THEME.name.upper()}\n", f"dim {P()}"),
    )
    tbl = Table.grid(padding=(0, 2))
    for _ in range(4):
        tbl.add_column()
    items = list(ThemeManager.THEMES.items())
    for i in range(0, len(items), 4):
        row = []
        for name, colors in items[i:i+4]:
            active = " ◀" if name == THEME.name else ""
            cell = Text()
            cell.append("  ██  ", style=f"bold {colors['primary']}")
            cell.append(name,     style=f"bold {colors['primary']}")
            cell.append(active,   style=f"dim {colors['dim']}")
            row.append(cell)
        while len(row) < 4:
            row.append(Text(""))
        tbl.add_row(*row)
    hint = Text.assemble(
        ("\n  /theme <name>  e.g. ", f"dim {D()}"),
        ("/theme purple",             f"bold {A()}"),
    )
    body = Table.grid(); body.add_column()
    body.add_row(header); body.add_row(tbl); body.add_row(hint)
    console.print(Panel(
        body,
        title=f"[bold {P()}]◈ THEME SELECTOR ◈[/bold {P()}]",
        border_style=P(), box=box.DOUBLE_EDGE, padding=(1, 1),
    ))


# ──────────────────────────────────────────────
# SECURITY / TRUST PROMPT
# ──────────────────────────────────────────────
def trust_folder_ui() -> None:
    folder = os.getcwd()
    CONSOLE.clear()

    # Rainbow colors — one per ASCII art row
    RAINBOW = [
        "#ff0000",  # red
        "#ff6600",  # orange
        "#ffe600",  # yellow
        "#39ff14",  # green
        "#00f5ff",  # cyan
        "#0066ff",  # blue
        "#bf5fff",  # violet
    ]

    art = Text(justify="center")
    art.append("\n")
    art.append("  ██████╗██╗     ██╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗\n", style=f"bold {RAINBOW[0]}")
    art.append("  ██╔════╝██║     ██║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝\n", style=f"bold {RAINBOW[1]}")
    art.append("  ██║     ██║     ██║     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   \n", style=f"bold {RAINBOW[2]}")
    art.append("  ██║     ██║     ██║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   \n", style=f"bold {RAINBOW[3]}")
    art.append("  ╚██████╗███████╗███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   \n", style=f"bold {RAINBOW[4]}")
    art.append("   ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   \n", style=f"bold {RAINBOW[5]}")
    art.append("\n")

    # Rainbow subtitle — each word a different color
    subtitle = Text(justify="center")
    words = ["CLI", "-", "AGENT", "  //  ", "SECURITY", "CHECK"]
    for i, w in enumerate(words):
        subtitle.append(w, style=f"bold {RAINBOW[i % len(RAINBOW)]}")
    subtitle.append("\n")
    art.append_text(subtitle)
    art.append("\n")

    # Rainbow border cycles through colors for the panel title
    rb_title = Text()
    label = " Security Check "
    for i, ch in enumerate(label):
        rb_title.append(ch, style=f"bold {RAINBOW[i % len(RAINBOW)]}")

    CONSOLE.print(Panel(
        art,
        title=rb_title,
        subtitle="[dim white]v1.0.0[/dim white]",
        border_style="white",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    ))

    # Rainbow CWD line — each path segment a different color
    cwd_line = Text()
    cwd_line.append("  Current Directory  ", style="bold white")
    parts = folder.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part:
            cwd_line.append("/", style=f"dim {RAINBOW[i % len(RAINBOW)]}")
            cwd_line.append(part, style=f"bold {RAINBOW[i % len(RAINBOW)]}")
    CONSOLE.print(cwd_line)
    CONSOLE.print()

    # Rainbow prompt question
    question = Text()
    question_str = "\n ? Trust this folder and enable file/shell access?"
    for i, ch in enumerate(question_str):
        question.append(ch, style=f"bold {RAINBOW[i % len(RAINBOW)]}")

    answer = Prompt.ask(question, choices=["y", "n"], default="n")

    if answer != "y":
        # Rainbow denied message
        denied = Text(justify="center")
        denied.append("\n")
        msg = "  Access Denied. Folder not trusted. Exiting...  "
        for i, ch in enumerate(msg):
            denied.append(ch, style=f"bold {RAINBOW[i % len(RAINBOW)]}")
        denied.append("\n")
        CONSOLE.print(Panel(denied, title="[bold red]Terminated[/bold red]",
                            border_style="red", box=box.DOUBLE_EDGE))
        raise SystemExit(0)

    # Rainbow success message
    success = Text(justify="center")
    success.append("\n")
    msg = "  Environment Trusted. Initializing Neural Engine...  "
    for i, ch in enumerate(msg):
        success.append(ch, style=f"bold {RAINBOW[i % len(RAINBOW)]}")
    success.append("\n")
    CONSOLE.print(Panel(success, border_style="white", box=box.DOUBLE_EDGE))
    time.sleep(0.6)


# ──────────────────────────────────────────────
# LIVE STATUS RENDERER
# ──────────────────────────────────────────────
class AgentStatusRenderer:
    def __init__(self):
        self.phase: str = "thinking"
        self.tool_name: Optional[str] = None
        self.tool_args: Optional[str] = None
        self.completed_tools: List[str] = []

    def set_thinking(self):
        self.phase = "thinking"; self.tool_name = None; self.tool_args = None

    def set_tool(self, name: str, args: str = ""):
        self.phase = "tool"; self.tool_name = name; self.tool_args = args

    def add_completed(self, name: str):
        self.completed_tools.append(name); self.phase = "thinking"; self.tool_name = None

    def set_done(self):
        self.phase = "done"

    def __rich__(self):
        rows = []
        for t in self.completed_tools:
            done = Text()
            done.append("  ✔  ", style=f"bold {S()}")
            done.append(t,       style=f"dim {S()}")
            rows.append(done)

        if self.phase == "thinking":
            rows.append(Spinner("dots", text=Text(
                " agent is thinking…", style=f"bold {P()}"
            )))
        elif self.phase == "tool":
            tool_line = Text()
            tool_line.append("  ⚙  executing  ", style=f"bold {W()}")
            tool_line.append(self.tool_name or "?", style=f"bold black on {W()}")
            if self.tool_args:
                tool_line.append(f"  {self.tool_args}", style=f"dim {P()}")
            rows.append(Spinner("point", text=tool_line))
        elif self.phase == "done":
            rows.append(Text("  ✔  finished", style=f"bold {S()}"))

        grid = Table.grid(padding=(0, 0)); grid.add_column()
        for r in rows:
            grid.add_row(r)

        phase_color = {"thinking": P(), "tool": W(), "done": S()}.get(self.phase, P())
        return Panel(
            grid,
            title=f"[bold {phase_color}]AGENT STATUS[/bold {phase_color}]",
            border_style=phase_color, box=box.ROUNDED, padding=(0, 1),
        )


# ──────────────────────────────────────────────
# CHAT UI
# ──────────────────────────────────────────────
class ChatUI:
    def __init__(self, agent):
        self.agent   = agent
        self.console = CONSOLE
        self.history: List[str] = []

    # ── shared helpers ────────────────────────
    def _ts_row(self, label: str) -> Table:
        h = Table.grid(expand=True)
        h.add_column(ratio=1); h.add_column(justify="right")
        h.add_row(Text(label, style=f"bold {P()}"), _animated_timestamp())
        return h

    def _body(self, *rows) -> Table:
        t = Table.grid(); t.add_column()
        for r in rows: t.add_row(r)
        return t

    # ── renders ───────────────────────────────
    def _render_header(self) -> None:
        left = Text.assemble(
            ("🚀 AI CONTROLLER ACTIVE", f"bold {P()}"),
        )
        right = Text.assemble(
            ("Type ", f"dim {D()}"),
            ("/help", f"bold {P()}"),
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
            title=f"[bold]SYSTEM LOG[/bold]",
            border_style=c, box=box.SQUARE,
        ))

    def _render_usage(self) -> None:
        usage = self.agent.get_last_usage() if hasattr(self.agent, "get_last_usage") else None
        if not usage:
            self._render_system("No usage data available.", A()); return
        table = Table(title="LLM Token Usage", box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Metric", style=f"{P()}")
        table.add_column("Value",  style=f"bold {W()}")
        for k, v in usage.items():
            table.add_row(str(k), str(v))
        self.console.print(table)

    def _render_live_clock(self, duration: float = 5.0) -> None:
        with Live(LiveClock(), console=self.console, refresh_per_second=10, transient=True):
            time.sleep(duration)

    # ── /theme handler ────────────────────────
    def _handle_theme(self, cmd: str) -> None:
        parts = cmd.strip().split()
        if len(parts) == 1:
            _render_theme_preview(self.console)
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

    # ── prompt label ─────────────────────────
    def _get_prompt_label(self) -> str:
        user = os.getenv("USERNAME") or os.getenv("USER") or "user"
        host = os.uname().nodename if hasattr(os, "uname") else "localhost"
        cwd  = os.getcwd()

        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

        time_str = datetime.now(local_tz).strftime("%H:%M")

        return (
            f"[dim {D()}]{time_str}[/dim {D()}] "
            f"[bold {S()}]{user}@{host}[/bold {S()}]:"
            f"[bold {P()}]{cwd}[/bold {P()}]$ "
        )

    # ── agent runner ─────────────────────────
    async def _run_with_live_status(self, cmd: str) -> str:
        renderer      = AgentStatusRenderer()
        content_parts: List[str] = []
        with Live(renderer, console=self.console, refresh_per_second=12, transient=True):
            async for chunk in self.agent.handle_message(cmd):
                if chunk.startswith("\x00TOOL_START:"):
                    _, rest = chunk.split(":", 1)
                    name, _, args = rest.partition(":")
                    renderer.set_tool(name.strip(), args.strip())
                elif chunk.startswith("\x00TOOL_DONE:"):
                    renderer.add_completed(chunk.split(":", 1)[1].strip())
                else:
                    content_parts.append(chunk)
            renderer.set_done()
        return "".join(content_parts)

    # ── main loop ────────────────────────────
    async def run(self) -> None:
        self.console.clear()
        self._render_header()
        self._render_command_box()

        while True:
            try:
                user_input = await anyio.to_thread.run_sync(
                    lambda: Prompt.ask(self._get_prompt_label())
                )
            except (KeyboardInterrupt, EOFError):
                self.console.print(Text("\nInterrupted. Shutting down...", style=f"bold {A()}"))
                return

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

            self._render_user(cmd)
            self.history.append(cmd)

            try:
                content = await self._run_with_live_status(cmd)
                if content.strip():
                    self._render_assistant(content)
                else:
                    self._render_system("Agent returned an empty response.", A())
            except Exception as e:
                self._render_system(f"Execution Error: {str(e)}", A())