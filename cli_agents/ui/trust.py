import os
import time

from rich import box
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from .utils import CONSOLE


_RAINBOW = [
    "#ff0000",  # red
    "#ff6600",  # orange
    "#ffe600",  # yellow
    "#39ff14",  # green
    "#00f5ff",  # cyan
    "#0066ff",  # blue
    "#bf5fff",  # violet
]


def _rainbow_text(msg: str, *, justify: str = "left") -> Text:
    """Colorise every character with a cycling rainbow palette."""
    t = Text(justify=justify)
    for i, ch in enumerate(msg):
        t.append(ch, style=f"bold {_RAINBOW[i % len(_RAINBOW)]}")
    return t


def trust_folder_ui() -> None:
    folder = os.getcwd()
    CONSOLE.clear()

    # ── ASCII art banner ──────────────────────
    art = Text(justify="center")
    art.append("\n")
    art.append("  ██████╗██╗     ██╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗\n", style=f"bold {_RAINBOW[0]}")
    art.append("  ██╔════╝██║     ██║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝\n", style=f"bold {_RAINBOW[1]}")
    art.append("  ██║     ██║     ██║     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   \n", style=f"bold {_RAINBOW[2]}")
    art.append("  ██║     ██║     ██║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   \n", style=f"bold {_RAINBOW[3]}")
    art.append("  ╚██████╗███████╗███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   \n", style=f"bold {_RAINBOW[4]}")
    art.append("   ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   \n", style=f"bold {_RAINBOW[5]}")
    art.append("\n")

    subtitle = Text(justify="center")
    for i, w in enumerate(["CLI", "-", "AGENT", "  //  ", "SECURITY", "CHECK"]):
        subtitle.append(w, style=f"bold {_RAINBOW[i % len(_RAINBOW)]}")
    subtitle.append("\n")
    art.append_text(subtitle)
    art.append("\n")

    rb_title = Text()
    for i, ch in enumerate(" Security Check "):
        rb_title.append(ch, style=f"bold {_RAINBOW[i % len(_RAINBOW)]}")

    CONSOLE.print(Panel(
        art,
        title=rb_title,
        subtitle="[dim white]v1.0.0[/dim white]",
        border_style="white",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    ))

    # ── CWD display ───────────────────────────
    cwd_line = Text()
    cwd_line.append("  Current Directory  ", style="bold white")
    parts = folder.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part:
            cwd_line.append("/",  style=f"dim {_RAINBOW[i % len(_RAINBOW)]}")
            cwd_line.append(part, style=f"bold {_RAINBOW[i % len(_RAINBOW)]}")
    CONSOLE.print(cwd_line)
    CONSOLE.print()

    # ── Prompt ────────────────────────────────
    answer = Prompt.ask(
        _rainbow_text("\n ? Trust this folder and enable file/shell access?"),
        choices=["y", "n"],
        default="n",
    )

    if answer != "y":
        denied = Text(justify="center")
        denied.append("\n")
        denied.append_text(_rainbow_text("  Access Denied. Folder not trusted. Exiting...  ", justify="center"))
        denied.append("\n")
        CONSOLE.print(Panel(denied, title="[bold red]Terminated[/bold red]",
                            border_style="red", box=box.DOUBLE_EDGE))
        raise SystemExit(0)

    success = Text(justify="center")
    success.append("\n")
    success.append_text(_rainbow_text("  Environment Trusted. Initializing Neural Engine...  ", justify="center"))
    success.append("\n")
    CONSOLE.print(Panel(success, border_style="white", box=box.DOUBLE_EDGE))
    time.sleep(0.6)