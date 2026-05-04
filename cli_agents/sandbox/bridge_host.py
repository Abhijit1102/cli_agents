"""
cli_agents/sandbox/bridge_host.py
Host-side bridge: writes cmd.json, polls for out.json.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


BRIDGE_CMD_FILE  = "bridge_cmd.json"
BRIDGE_OUT_FILE  = "bridge_out.json"
BRIDGE_READY     = ".bridge_ready"
POLL_INTERVAL    = 0.25
STARTUP_TIMEOUT  = 180.0  # Increased timeout for readiness


class BridgeTimeout(Exception):
    pass


class HostBridge:
    def __init__(self, shared_folder: Path):
        self.shared = shared_folder

    @property
    def _cmd_path(self) -> Path:
        return self.shared / BRIDGE_CMD_FILE

    @property
    def _out_path(self) -> Path:
        return self.shared / BRIDGE_OUT_FILE

    @property
    def _ready_path(self) -> Path:
        return self.shared / BRIDGE_READY

    def wait_for_ready(self, timeout: float = STARTUP_TIMEOUT) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._ready_path.exists():
                return
            time.sleep(POLL_INTERVAL)
        raise BridgeTimeout(
            f"Sandbox agent did not become ready within {timeout}s. "
            f"Check bootstrap logs in: {self.shared}"
        )

    def send(self, prompt: str, timeout: float = 120.0) -> str:
        msg_id = uuid.uuid4().hex[:8]

        self._out_path.unlink(missing_ok=True)

        payload = {"id": msg_id, "prompt": prompt}
        self._cmd_path.write_text(json.dumps(payload), encoding="utf-8")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._out_path.exists():
                try:
                    raw = json.loads(self._out_path.read_text(encoding="utf-8"))
                    if raw.get("id") == msg_id:
                        self._out_path.unlink(missing_ok=True)
                        self._cmd_path.unlink(missing_ok=True)
                        return raw.get("response", "")
                except (json.JSONDecodeError, OSError):
                    pass
            time.sleep(POLL_INTERVAL)

        raise BridgeTimeout(f"No response from sandbox agent within {timeout}s.")