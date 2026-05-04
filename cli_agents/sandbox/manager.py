"""
cli_agents/sandbox/manager.py
Windows Sandbox lifecycle manager.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SandboxSession:
    id: str
    wsb_path: Path
    log_dir: Path
    created_at: str
    status: str = "created"
    shared_folder: Optional[Path] = None
    pid: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "wsb_path":      str(self.wsb_path),
            "log_dir":       str(self.log_dir),
            "created_at":    self.created_at,
            "status":        self.status,
            "shared_folder": str(self.shared_folder) if self.shared_folder else None,
            "pid":           self.pid,
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


# ── Registry ──────────────────────────────────────────────────────────────────

class SandboxRegistry:
    def __init__(self, registry_path: Path):
        self.path = registry_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SandboxSession] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._sessions = {
                    k: SandboxSession.from_dict(v) for k, v in raw.items()
                }
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


# ── Manager ───────────────────────────────────────────────────────────────────

class SandboxManager:
    """
    Manages Windows Sandbox instances.

    Flow:
        manager = SandboxManager(project_root)
        session = manager.create(shared_folder=project_root)
        manager.prepare_share(session.id)   # copies bootstrap + package
        manager.run(session.id)
        bridge  = manager.attach(session.id) # waits for .bridge_ready
        reply   = bridge.send("write hello.py")
        manager.destroy(session.id)
    """

    # Bootstrap runs from the share via LogonCommand
    WSB_TEMPLATE = """\
<Configuration>
  <VGpu>Enable</VGpu>
  <Networking>Enable</Networking>
  <LogonCommand>
    <Command>powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\\HostShare\\bootstrap.ps1"</Command>
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
        self.sandbox_dir  = project_root / ".sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.registry = SandboxRegistry(self.sandbox_dir / "registry.json")

    # ── internal helpers ──────────────────────────────────────────────────────

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
            mapped = self.MAPPED_FOLDER_BLOCK.format(
                host_path=str(shared_folder)
            )
        wsb = self._wsb_path(sid)
        wsb.write_text(
            self.WSB_TEMPLATE.format(mapped_folders=mapped),
            encoding="utf-8",
        )
        return wsb

    def _ps(self, script: str, capture: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=capture,
            text=True,
        )

    # ── public API ────────────────────────────────────────────────────────────

    def create(self, shared_folder: Optional[Path] = None) -> SandboxSession:
        sid     = self._new_id()
        wsb     = self._build_wsb(sid, shared_folder)
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

    def prepare_share(self, sid: str) -> tuple[bool, str]:
        """
        Copies bootstrap.ps1 and the cli_agents package into the shared folder
        so the sandbox can install and run everything without internet access.
        
        Call this after create() and before run().
        """
        session = self.registry.get(sid)
        if session is None:
            return False, f"No session '{sid}'."
        if not session.shared_folder:
            return False, "Session has no shared folder."

        share = session.shared_folder
        errors: list[str] = []

        # 1. Copy bootstrap.ps1
        src_bootstrap = Path(__file__).parent / "bootstrap.ps1"
        dst_bootstrap = share / "bootstrap.ps1"
        if src_bootstrap.exists():
            shutil.copy2(src_bootstrap, dst_bootstrap)
        else:
            errors.append(f"bootstrap.ps1 not found at {src_bootstrap}")

        # 2. Mirror the cli_agents package into share/cli_agents
        #    so bridge_sandbox.py can be found at C:\HostShare\cli_agents\sandbox\bridge_sandbox.py
        src_pkg = Path(__file__).parent.parent   # cli_agents/ root
        dst_pkg = share / "cli_agents"
        if dst_pkg.exists():
            shutil.rmtree(dst_pkg)
        shutil.copytree(src_pkg, dst_pkg, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".venv", ".git", ".sandbox",
        ))

        # 3. Copy .env from project root if present
        env_src = self.project_root / ".env"
        if env_src.exists():
            shutil.copy2(env_src, share / ".env")

        if errors:
            return False, "Partial prepare: " + "; ".join(errors)
        return True, f"Share prepared at {share}"

    def run(self, sid: str) -> tuple[bool, str]:
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}'."
        if session.status == "running":
            return False, f"Sandbox '{sid}' is already running."
        if session.status == "destroyed":
            return False, f"Sandbox '{sid}' has been destroyed."

        try:
            proc = subprocess.Popen(
                ["WindowsSandbox.exe", str(session.wsb_path)],
                shell=False,
            )
            session.status = "running"
            session.pid    = proc.pid
            self.registry.update(session)
            return True, f"Sandbox '{sid}' launched (pid={proc.pid})."
        except FileNotFoundError:
            return False, (
                "WindowsSandbox.exe not found. Enable it with:\n"
                "  Enable-WindowsOptionalFeature -Online "
                "-FeatureName Containers-DisposableClientVM -All"
            )
        except Exception as exc:
            return False, f"Failed to launch sandbox: {exc}"

    def attach(self, sid: str) -> "HostBridge":
        """
        Returns a HostBridge for a running sandbox.
        Blocks until the sandbox bridge signals readiness (.bridge_ready).
        """
        from .bridge_host import HostBridge, BridgeTimeout

        session = self.registry.get(sid)
        if session is None:
            raise ValueError(f"No sandbox with id '{sid}'.")
        if session.status != "running":
            raise RuntimeError(
                f"Sandbox '{sid}' is not running (status={session.status})."
            )
        if not session.shared_folder:
            raise RuntimeError("Session has no shared folder — cannot bridge.")

        bridge = HostBridge(session.shared_folder)
        bridge.wait_for_ready()
        return bridge

    def exec(self, sid: str, command: str, timeout: int = 30) -> tuple[bool, str]:
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}'."
        if session.status != "running":
            return False, f"Sandbox '{sid}' is not running (status={session.status})."

        if session.shared_folder:
            script_path = session.shared_folder / f"_sandbox_exec_{sid}.ps1"
            script_path.write_text(command, encoding="utf-8")
            result = self._ps(f"& '{script_path}'")
            try:
                script_path.unlink()
            except OSError:
                pass
            ok     = result.returncode == 0
            output = (result.stdout or "") + (result.stderr or "")
            return ok, output.strip()

        result = self._ps(command)
        ok     = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return ok, output.strip()

    def destroy(self, sid: str) -> tuple[bool, str]:
        session = self.registry.get(sid)
        if session is None:
            return False, f"No sandbox with id '{sid}'."
        if session.status == "destroyed":
            return False, f"Sandbox '{sid}' is already destroyed."

        if session.pid:
            self._ps(
                f"Stop-Process -Id {session.pid} -Force -ErrorAction SilentlyContinue"
            )

        self._ps(
            f"Get-Process WindowsSandbox -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.MainWindowTitle -like '*{sid}*' }} | "
            f"Stop-Process -Force -ErrorAction SilentlyContinue"
        )

        # Remove .wsb
        try:
            session.wsb_path.unlink(missing_ok=True)
        except OSError:
            pass

        # Clean up bridge sentinel files in the share
        if session.shared_folder:
            for fname in (".bridge_ready", "bridge_cmd.json", "bridge_out.json"):
                try:
                    (session.shared_folder / fname).unlink(missing_ok=True)
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