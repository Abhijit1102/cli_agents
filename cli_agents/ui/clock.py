import time
from datetime import datetime

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .theme import THEME, P, D, A, S, SH
from .utils import local_tz


# ──────────────────────────────────────────────
# ANIMATED TIMESTAMP
# ──────────────────────────────────────────────
def animated_timestamp() -> Text:
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
# LIVE CLOCK (Rich renderable)
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
def render_theme_preview(console: Console) -> None:
    header = Text.assemble(
        ("◈ AVAILABLE THEMES ◈\n",             f"bold {P()}"),
        (f"  current → {THEME.name.upper()}\n", f"dim {P()}"),
    )
    tbl = Table.grid(padding=(0, 2))
    for _ in range(4):
        tbl.add_column()
    items = list(THEME.THEMES.items())
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