from typing import List, Optional, Tuple

from rich import box
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.status import Status

from .theme import P, W, S, D, A


class AgentStatusRenderer:
    """Live Rich renderable — tracks agent phase and tool calls."""

    def __init__(self):
        self.phase: str = "thinking"
        self.tool_name: Optional[str] = None
        self.tool_args: Optional[str] = None
        # Each entry: (name, is_mcp)
        self.completed_tools: List[Tuple[str, bool]] = []
        self.is_mcp: bool = False

    def set_thinking(self) -> None:
        self.phase     = "thinking"
        self.tool_name = None
        self.tool_args = None
        self.is_mcp    = False

    def set_tool(self, name: str, args: str = "", is_mcp: bool = False) -> None:
        self.phase     = "tool"
        self.tool_name = name
        self.tool_args = args
        self.is_mcp    = is_mcp

    def add_completed(self, name: str) -> None:
        self.completed_tools.append((name, self.is_mcp))
        self.phase     = "thinking"
        self.tool_name = None
        self.is_mcp    = False

    def set_done(self) -> None:
        self.phase = "done"

    def __rich__(self) -> Panel:
        rows = []

        for tool_name, tool_is_mcp in self.completed_tools:
            done = Text()
            if tool_is_mcp:
                # MCP tools: teal checkmark + [MCP] badge
                done.append("  ✔  ", style=f"bold {A()}")
                done.append("[MCP] ", style=f"bold {A()}")
                done.append(tool_name, style=f"dim {A()}")
            else:
                done.append("  ✔  ", style=f"bold {S()}")
                done.append(tool_name, style=f"dim {S()}")
            rows.append(done)

        if self.phase == "thinking":
            rows.append(
                Status(
                    "[bold yellow]🚀 thinking • evaluating • deciding…[/bold yellow]",
                    spinner="line",
                )
            )
        elif self.phase == "tool":
            tool_line = Text()
            if self.is_mcp:
                # MCP: distinct amber/yellow colour + 🔌 icon
                tool_line.append("  🔌  mcp  ", style=f"bold {A()}")
                tool_line.append(self.tool_name or "?", style=f"bold black on {A()}")
                if self.tool_args:
                    tool_line.append(f"  🧾 args  {self.tool_args}", style=f"dim {P()}")
                rows.append(Spinner("dots2", text=tool_line))
            else:
                tool_line.append("  ⚙  executing  ", style=f"bold {W()}")
                tool_line.append(self.tool_name or "?", style=f"bold black on {W()}")
                if self.tool_args:
                    tool_line.append(f"  🧾 args  {self.tool_args}", style=f"dim {P()}")
                rows.append(Spinner("point", text=tool_line))
        elif self.phase == "done":
            rows.append(Text("  ✔  finished", style=f"bold {S()}"))

        grid = Table.grid(padding=(0, 0))
        grid.add_column()
        for r in rows:
            grid.add_row(r)

        if self.is_mcp:
            phase_color = A()
        else:
            phase_color = {"thinking": P(), "tool": W(), "done": S()}.get(self.phase, P())

        return Panel(
            grid,
            title=f"[bold {phase_color}]AGENT STATUS[/bold {phase_color}]",
            border_style=phase_color, box=box.ROUNDED, padding=(0, 1),
        )