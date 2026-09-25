from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from cli_agents.ui.theme import P, D, A, S, W

class SystemPathRenderer:
    """
    Renders a visual indicator of which AI system is currently active.
    """
    @staticmethod
    def render_system1() -> Panel:
        """Render System 1 (Jev AI) badge."""
        content = Table.grid(padding=(0, 0))
        content.add_column()
        
        badge = Text()
        badge.append(" ⚡ SYSTEM 1 ", style=f"bold black on {P()}")
        badge.append(" [Jev AI] ", style=f"bold {P()}")
        badge.append(" ➔ Reflexive Path: Fast, Intuitive Decision", style=f"italic dim {D()}")
        
        content.add_row(badge)
        
        return Panel(
            content,
            border_style=P(),
            box=box.DOUBLE,
            padding=(0, 1),
            title=f"[bold {P()}]⚡ SYSTEM 1 ACTIVE[/bold {P()}]",
            subtitle=f"[{P()}]Low Latency Mode"
        )

    @staticmethod
    def render_system2() -> Panel:
        """Render System 2 (Main LLM) badge."""
        content = Table.grid(padding=(0, 0))
        content.add_column()
        
        badge = Text()
        badge.append(" 🧠 SYSTEM 2 ", style=f"bold black on {A()}")
        badge.append(" [Main LLM] ", style=f"bold {A()}")
        badge.append(" ➔ Deliberative Path: Reasoning & Tool Use", style=f"italic dim {D()}")
        
        content.add_row(badge)
        
        return Panel(
            content,
            border_style=A(),
            box=box.DOUBLE,
            padding=(0, 1),
            title=f"[bold {A()}]🧠 SYSTEM 2 ACTIVE[/bold {A()}]",
            subtitle=f"[{A()}]Deep Thinking Mode"
        )
