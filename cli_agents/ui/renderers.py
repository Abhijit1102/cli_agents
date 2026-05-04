from typing import List, Optional

from rich import box
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .theme import P, W, S, D, A


class AgentStatusRenderer:
    """Live Rich renderable — tracks agent phase and tool calls."""

    def __init__(self):
        self.phase: str = "thinking"
        self.tool_name: Optional[str] = None
        self.tool_args: Optional[str] = None
        self.completed_tools: List[str] = []

    # ── state mutators ────────────────────────
    def set_thinking(self) -> None:
        self.phase     = "thinking"
        self.tool_name = None
        self.tool_args = None

    def set_tool(self, name: str, args: str = "") -> None:
        self.phase     = "tool"
        self.tool_name = name
        self.tool_args = args

    def add_completed(self, name: str) -> None:
        self.completed_tools.append(name)
        self.phase     = "thinking"
        self.tool_name = None

    def set_done(self) -> None:
        self.phase = "done"

    # ── Rich protocol ─────────────────────────
    def __rich__(self) -> Panel:
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

        grid = Table.grid(padding=(0, 0))
        grid.add_column()
        for r in rows:
            grid.add_row(r)

        phase_color = {"thinking": P(), "tool": W(), "done": S()}.get(self.phase, P())
        return Panel(
            grid,
            title=f"[bold {phase_color}]AGENT STATUS[/bold {phase_color}]",
            border_style=phase_color, box=box.ROUNDED, padding=(0, 1),
        )