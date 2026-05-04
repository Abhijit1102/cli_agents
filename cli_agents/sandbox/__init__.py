"""
cli_agents/sandbox/__init__.py

Sandbox sub-package: Windows Sandbox lifecycle management.

Public surface:
    SandboxManager   — create / run / exec / destroy sessions
    SandboxSession   — session data model
    handle_sandbox_command — ChatUI slash-command dispatcher
"""

from .manager import SandboxManager, SandboxSession
from .commands import handle_sandbox_command

__all__ = ["SandboxManager", "SandboxSession", "handle_sandbox_command"]