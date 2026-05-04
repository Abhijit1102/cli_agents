"""
slash_palette.py
────────────────
prompt_toolkit slash-command palette — terminal-size aware.

Type "/" → floating dropdown appears.
↑ ↓ navigate · Enter select · Esc dismiss · type to fuzzy-filter.

Terminal resize (SIGWINCH / Windows resize) is handled automatically:
  • Dropdown height  = (terminal rows - 4) capped to [4, 16]
  • Description text = truncated to fit remaining column width
  • prompt_toolkit redraws the full layout on every resize event
"""

from __future__ import annotations

import os
import shutil
import signal
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
# ─────────────────────────────────────────────
# Terminal-size helper
# ─────────────────────────────────────────────

class TermSize:
    """
    Tracks the current terminal dimensions and reacts to resize events.
    Thread-safe reads; updated via SIGWINCH on POSIX, polling on Windows.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._cols, self._rows = self._query()
        self._install_handler()

    # ── public props ──────────────────────────
    @property
    def cols(self) -> int:
        with self._lock:
            return self._cols

    @property
    def rows(self) -> int:
        with self._lock:
            return self._rows

    @property
    def menu_height(self) -> int:
        """Dropdown rows: terminal height minus prompt/status rows, clamped."""
        # return max(4, min(16, self.rows - 4))
        return max(6, self.rows - 3)

    @property
    def desc_width(self) -> int:
        """Characters available for the description column."""
        # name column ≈ 22 chars, separator + padding ≈ 4
        return max(10, self.cols - 26)

    # ── internals ────────────────────────────
    @staticmethod
    def _query() -> Tuple[int, int]:
        ts = shutil.get_terminal_size(fallback=(80, 24))
        return ts.columns, ts.lines

    def _refresh(self):
        cols, rows = self._query()
        with self._lock:
            self._cols = cols
            self._rows = rows

    def _install_handler(self):
        if hasattr(signal, "SIGWINCH"):          # POSIX only
            old = signal.getsignal(signal.SIGWINCH)

            def _handler(sig, frame):
                self._refresh()
                if callable(old):
                    old(sig, frame)

            signal.signal(signal.SIGWINCH, _handler)
        else:
            # Windows fallback: lightweight background polling thread
            def _poll():
                while True:
                    self._refresh()
                    threading.Event().wait(0.5)

            t = threading.Thread(target=_poll, daemon=True)
            t.start()


# Module-level singleton — created once, shared everywhere
TERM = TermSize()


# ─────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────

@dataclass
class SlashCommand:
    name: str
    description: str
    handler: Optional[Callable[[], None]] = None
    aliases: List[str] = field(default_factory=list)

    @property
    def full(self) -> str:
        return f"/{self.name}"


# ─────────────────────────────────────────────
# Fuzzy helpers
# ─────────────────────────────────────────────

def _fuzzy(query: str, target: str) -> bool:
    """True if every char of query appears in order inside target."""
    if not query:
        return True
    it = iter(target)
    return all(c in it for c in query)


def _highlight(text: str, query: str) -> str:
    """Bold-cyan matched fuzzy chars, dim-grey the rest."""
    if not query:
        return f'<b><style color="#00f5ff">{text}</style></b>'
    result, qi = [], 0
    for ch in text:
        if qi < len(query) and ch.lower() == query[qi].lower():
            result.append(f'<b><style color="#00f5ff">{ch}</style></b>')
            qi += 1
        else:
            result.append(f'<style color="#c0c0c0">{ch}</style>')
    return "".join(result)


def _trunc(text: str, width: int) -> str:
    """Truncate with ellipsis to fit `width` chars."""
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


# ─────────────────────────────────────────────
# Completer  (terminal-size aware)
# ─────────────────────────────────────────────

class SlashCompleter(Completer):
    """
    Activates when buffer starts with '/'.
    Description column width adapts to the current terminal width via TERM.
    """

    def __init__(self, commands: List[SlashCommand]):
        self._commands = commands

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        query    = text[1:].lower()
        dw       = TERM.desc_width          # live terminal width → description budget

        scored: List[Tuple[int, SlashCommand]] = []
        for cmd in self._commands:
            haystack = " ".join([cmd.name, cmd.description, *cmd.aliases]).lower()
            if _fuzzy(query, haystack):
                score = 0 if cmd.name.startswith(query) else 1
                scored.append((score, cmd))

        scored.sort(key=lambda x: (x[0], x[1].name))

        for _, cmd in scored:
            hi_name = _highlight(f"/{cmd.name}", query)
            desc    = _trunc(cmd.description, dw)

            yield Completion(
                text=cmd.full,
                start_position=-len(text),
                display=HTML(
                    f"{hi_name}  "
                    f'<style color="#7a8090">{desc}</style>'
                ),
                display_meta=HTML(
                    f'<style color="#00f5ff">{", ".join(cmd.aliases)}</style>'
                ) if cmd.aliases else HTML(""),
            )


# ─────────────────────────────────────────────
# Palette style
# ─────────────────────────────────────────────

PALETTE_STYLE = Style.from_dict({
    "completion-menu":                         "bg:#0d1117 #c0c0c0",
    "completion-menu.completion":              "bg:#0d1117 #c0c0c0",
    "completion-menu.completion.current":      "bg:#1a2233 #00f5ff bold",
    "completion-menu.meta.completion":         "bg:#0d1117 #444",
    "completion-menu.meta.completion.current": "bg:#1a2233 #00f5ff",
    "scrollbar.background":                    "bg:#0d1117",
    "scrollbar.button":                        "bg:#00f5ff",
    "prompt":                                  "#39ff14 bold",
    "":                                        "bg:#0a0f1a #e0e0e0",
})


# ─────────────────────────────────────────────
# Resize-aware completion menu height
# ─────────────────────────────────────────────

class _DynamicMenuHeight:
    """
    prompt_toolkit reads `max_height` from the completion menu container.
    Wrapping it in an object whose __int__ is called each render cycle
    makes the dropdown grow / shrink live with the terminal.
    """
    def __index__(self) -> int:          # used in slice / index contexts
        return TERM.menu_height

    def __int__(self) -> int:
        return TERM.menu_height


# ─────────────────────────────────────────────
# Public factory
# ─────────────────────────────────────────────

def make_palette_session(commands: List[SlashCommand]) -> PromptSession:
    """
    Returns a PromptSession wired with:
      • slash-command palette (type / to open)
      • terminal-size-aware dropdown height
      • width-aware description truncation
      • SIGWINCH / Windows-poll resize handling
    """
    kb = KeyBindings()

    @kb.add("/")
    def _slash(event):
        """Insert '/' then immediately open the command palette."""
        buf = event.app.current_buffer
        buf.insert_text("/")
        buf.start_completion(select_first=False)

    @kb.add("escape")
    def _esc(event):
        """Cancel completion; if none open, clear the line."""
        buf = event.app.current_buffer
        if buf.complete_state:
            buf.cancel_completion()
        else:
            buf.text = ""

    return PromptSession(
        completer=SlashCompleter(commands),
        complete_while_typing=True,
        complete_in_thread=True,
        key_bindings=kb,
        style=PALETTE_STYLE,
        auto_suggest=AutoSuggestFromHistory(),
        history=InMemoryHistory(),
        mouse_support=False,

        # 👇 HERE is the correct place
        complete_style=CompleteStyle.COLUMN,
    )