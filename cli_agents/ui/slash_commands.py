"""
slash_commands.py
─────────────────
Command registry + ask_with_palette() — drop-in for Prompt.ask().

Terminal-size integration:
  • Dropdown height auto-adjusts via TERM.menu_height (SIGWINCH / poll)
  • Description column truncates to TERM.desc_width
  • Prompt label is right-truncated if the terminal is very narrow
"""

from __future__ import annotations

import re
from typing import List

from .slash_palette import SlashCommand, TERM, make_palette_session


# ─────────────────────────────────────────────
# Command registry
# ─────────────────────────────────────────────

COMMANDS: List[SlashCommand] = [
    SlashCommand("help", "Show all available commands", aliases=["?", "commands"]),
    SlashCommand("reset", "Wipe short-term agent memory", aliases=["clear-memory", "forget"]),
    SlashCommand("usage", "Check API token consumption", aliases=["tokens", "cost"]),
    SlashCommand("cwd", "Show current working directory", aliases=["pwd", "dir"]),
    SlashCommand("history", "Replay prompts from this session", aliases=["log", "past"]),
    SlashCommand("clear", "Reset screen view", aliases=["cls", "clean"]),
    SlashCommand("clock", "Show live system clock (5 s)", aliases=["time", "date"]),

    SlashCommand("theme", "List or switch colour theme", aliases=["color", "colour"]),
    SlashCommand("theme cyan", "Switch to cyan theme (default)", aliases=["cyan"]),
    SlashCommand("theme green", "Switch to green theme", aliases=["green"]),
    SlashCommand("theme purple", "Switch to purple theme", aliases=["purple"]),
    SlashCommand("theme yellow", "Switch to yellow theme", aliases=["yellow"]),
    SlashCommand("theme orange", "Switch to orange theme", aliases=["orange"]),
    SlashCommand("theme pink", "Switch to pink theme", aliases=["pink"]),
    SlashCommand("theme white", "Switch to white theme", aliases=["white"]),
    SlashCommand("config", "Display current MODEL and environment (.env) settings used by CLI_agents"),
    SlashCommand("init_project",  "Read codebase and write PROJECT_DESCRIPTION.md"),

    SlashCommand(
        "sandbox",
        "Manage sandbox environments (create/run/exec/destroy/list/status)",
        aliases=["sb"]
    ),
]


# ─────────────────────────────────────────────
# Session singleton
# ─────────────────────────────────────────────

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = make_palette_session(COMMANDS)
    return _session


# ─────────────────────────────────────────────
# Prompt label helpers
# ─────────────────────────────────────────────

def _strip_rich(text: str) -> str:
    """Remove Rich markup tags → plain text."""
    return re.sub(r"\[/?[^\]]+\]", "", text)


def _fit_label(label: str) -> str:
    """
    If the terminal is very narrow, right-truncate the prompt label
    so the input area always has at least 20 chars of breathing room.
    """
    cols       = TERM.cols
    min_input  = 20
    max_label  = max(8, cols - min_input)
    plain      = _strip_rich(label)
    if len(plain) <= max_label:
        return plain
    return plain[: max_label - 1] + "… "


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def ask_with_palette(label: str) -> str:
    """
    Drop-in replacement for Prompt.ask().

    Shows an interactive prompt; typing '/' opens the slash-command palette.
    The dropdown height and description column width track the live terminal
    size — resize the window at any time and the UI adapts instantly.

    Returns the raw input string (empty string on EOF/cancel).
    """
    session    = _get_session()
    fit_label  = _fit_label(label)
    result     = session.prompt(fit_label)
    return result if result is not None else ""