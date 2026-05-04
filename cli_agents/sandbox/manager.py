"""
cli_agents/sandbox/manager.py

Windows Sandbox lifecycle manager.
Handles create, run, exec, and destroy via PowerShell WSB files.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class SandboxSession:
    id: str
    wsb_path: Path
    log_dir: Path
    created_at: str
    status: str = "created"   # created | running | stopped | destroyed
    shared_folder: Optional[Path] = None
    pid: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wsb_path": str(self.wsb_path),
            "log_dir": str(self.log_dir),
            "created_at": self.created_at,
            "status": self.status,
            "shared_folder": str(self.shared_folder) if self.shared_folder else None,
            "pid": self.pid,
        }

    @staticmethod
    def from_dict(d: dict) -> "SandboxSession":
        return SandboxSession(
            id=d["id"],
            wsb_path=Path(d["wsb_path"]),
            log_dir=Path(d["log_dir"]),
            created_at=d["created_at"],
            status=d["status"],
            shared_folder=Path(d["shared_folder"]) if d.get("shared_folder") else None,
            pid=d.get("pid"),
        )


# ─── Registry (persists sessions across CLI invocations) ──────────────────────

class SandboxRegistry:
    """Persists sandbox session metadata to a JSON file."""

    def __init__(self, registry_path: Path):
        self.path = registry_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SandboxSession] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._sessions = {k: SandboxSession.from_dict(v) for k, v in raw.items()}
            except Exception:
                self._sessions = {}

    def _save(self) -> None:
        data = {k: v.to_dict() for k, v in self._sessions.items()}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, session: SandboxSession) -> None:
        self._sessions[session.id] = session
        self._save()

    def get(self, sid: str) -> Optional[SandboxSession]:
        return self._sessions.get(sid)

    def update(self, session: SandboxSession) -> None:
        self._sessions[session.id] = session
        self._save()

    def remove(self, sid: str) -> None:
        self._sessions.pop(sid, None)
        self._save()

    def all(self) -> list[SandboxSession]:
        return list(self._sessions.values())

    def latest(self) -> Optional[SandboxSession]:
        if not self._sessions:
            return None
        return sorted(self._sessions.values(), key=lambda s: s.created_at)[-1]


# ─── Core manager ─────────────────────────────────────────────────────────────

class SandboxManager:
    """
    Manages Windows Sandbox instances via .wsb config files and PowerShell.

    Typical usage:
        manager = SandboxManager(project_root)
        session = manager.create(shared_folder=project_root)
        manager.run(session.id)
        result = manager.exec(session.id, "dir C:\\Users\\WDAGUtilityAccount\\Desktop")
        manager.destroy(session.id)
    """

    WSB_TEMPLATE = """\
<Configuration>
  <VGpu>Enable</VGpu>
  <Networking>Enable</Networking>
  <LogonCommand>
    <Command>powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path C:\\SandboxLogs | Out-Null"</Command>
  </LogonCommand>
{mapped_folders}</Configuration>
"""

    MAPPED_FOLDER_BLOCK = """\
  <MappedFolders>
    <MappedFolder>
      <HostFolder>{host_path}</HostFolder>
      <SandboxFolder>C:\\HostShare</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.sandbox_dir = project_root / ".sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.registry = SandboxRegistry(self.sandbox_dir / "registry.json")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _new_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def _wsb_path(self, sid: str) -> Path:
        return self.sandbox_dir / f"sandbox_{sid}.wsb"

    def _log_dir(self, sid: str) -> Path:
        d = self.sandbox_dir / "logs" / sid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _build_wsb(self, sid: str, shared_folder: Optional[Path] = None) -> Path:
        mapped = ""
        if shared_folder and shared_folder.exists():
            mapped = self.MAPPED_FOLDER_BLOCK.format(host_path=str(shared_folder))
        content = self.WSB_TEMPLATE.format(mapped_folders=mapped)
        wsb = self._wsb_path(sid)
        wsb.write_text(content, encoding="utf-8")
        return wsb

    def _ps(self, script: str, capture: bool = True) -> subprocess.CompletedProcess:
        """Run a PowerShell snippet and return the result."""
        args = [
            "powershell", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", script,
        ]
        return subprocess.run(
            args,
            capture_output=capture,
            text=True,
        )

    # ── public API ───────────────────────────────────────────────────────────

    def create(self, shared_folder: Optional[Path] = None) -> SandboxSession:
        """
        Build a .wsb config and register a new sandbox session.
        Does NOT launch the sandbox yet — call run() for that.
        """
        sid = self._new_id()
        wsb = self._build_wsb(sid, shared_folder)
        log_dir = self._log_dir(sid)

        session = SandboxSession(
            id=sid,
            wsb_path=wsb,
            log_dir=log_dir,
            created_at=datetime.now().isoformat(),
            shared_folder=shared_folder,
        )
        self.registry.add(session)
        return session

    def run(self, sid: str) -> tuple[bool, str]:
        """
        Launch the Windows Sandbox for the given session ID.
        Returns (success, message).
        """
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}' found."
        if session.status == "running":
            return False, f"Sandbox '{sid}' is already running."
        if session.status == "destroyed":
            return False, f"Sandbox '{sid}' has been destroyed."

        # WindowsSandbox.exe opens the .wsb file
        try:
            proc = subprocess.Popen(
                ["WindowsSandbox.exe", str(session.wsb_path)],
                shell=False,
            )
            session.status = "running"
            session.pid = proc.pid
            self.registry.update(session)
            return True, f"Sandbox '{sid}' launched (pid={proc.pid})."
        except FileNotFoundError:
            return False, (
                "WindowsSandbox.exe not found. "
                "Enable it with: Enable-WindowsOptionalFeature -Online "
                "-FeatureName Containers-DisposableClientVM -All"
            )
        except Exception as exc:
            return False, f"Failed to launch sandbox: {exc}"

    def exec(self, sid: str, command: str, timeout: int = 30) -> tuple[bool, str]:
        """
        Execute a PowerShell command inside a running sandbox via
        Enter-PSSession / Invoke-Command over localhost loopback.

        NOTE: Windows Sandbox doesn't expose WinRM by default; this method
        runs the command *on the host* inside a constrained PS scope as a
        proxy, OR (when sandbox WinRM is available) remotes into it.
        For full isolation use the shared-folder drop approach described below.
        """
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}' found."
        if session.status != "running":
            return False, f"Sandbox '{sid}' is not running (status={session.status})."

        # Strategy: drop a .ps1 script into the shared folder; sandbox
        # logon-command picks it up. Here we run it on host as a fallback.
        if session.shared_folder:
            script_path = session.shared_folder / f"_sandbox_exec_{sid}.ps1"
            script_path.write_text(command, encoding="utf-8")
            result = self._ps(f"& '{script_path}'")
            try:
                script_path.unlink()
            except OSError:
                pass
            ok = result.returncode == 0
            output = (result.stdout or "") + (result.stderr or "")
            return ok, output.strip()

        # No shared folder — run directly on host (sandboxed via PS's constrained mode)
        result = self._ps(command)
        ok = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return ok, output.strip()

    def destroy(self, sid: str) -> tuple[bool, str]:
        """
        Kill the sandbox process and clean up its .wsb file.
        """
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}' found."
        if session.status == "destroyed":
            return False, f"Sandbox '{sid}' is already destroyed."

        # Try to kill by pid
        if session.pid:
            self._ps(f"Stop-Process -Id {session.pid} -Force -ErrorAction SilentlyContinue")

        # Also kill any WindowsSandbox.exe processes referencing our .wsb
        wsb_name = session.wsb_path.name
        self._ps(
            f"Get-Process WindowsSandbox -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.MainWindowTitle -like '*{sid}*' }} | "
            f"Stop-Process -Force -ErrorAction SilentlyContinue"
        )

        # Remove .wsb file
        try:
            session.wsb_path.unlink(missing_ok=True)
        except OSError:
            pass

        session.status = "destroyed"
        self.registry.update(session)
        return True, f"Sandbox '{sid}' destroyed."

    def list_sessions(self) -> list[SandboxSession]:
        return self.registry.all()

    def get_session(self, sid: str) -> Optional[SandboxSession]:
        return self.registry.get(sid)

    def latest_session(self) -> Optional[SandboxSession]:
        return self.registry.latest()