import os
import zoneinfo

from rich.console import Console


def _make_console() -> Console:
    if os.name == "nt" and os.getenv("MSYSTEM"):
        return Console(force_terminal=True, color_system="truecolor")
    return Console(color_system="truecolor")


CONSOLE  = _make_console()
local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")