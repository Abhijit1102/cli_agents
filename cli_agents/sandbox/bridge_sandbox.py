"""
cli_agents/sandbox/bridge_sandbox.py
Runs INSIDE Windows Sandbox. Polls shared folder, runs agent, writes response.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

SHARE      = Path(r"C:\HostShare")
CMD_FILE   = SHARE / "bridge_cmd.json"
OUT_FILE   = SHARE / "bridge_out.json"
READY_FILE = SHARE / ".bridge_ready"
LOG_FILE   = SHARE / "bridge_sandbox.log"
POLL       = 0.3


def _log(msg: str) -> None:
    ts   = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


async def _run_agent(prompt: str) -> str:
    from cli_agents.config import load_env
    from cli_agents.core import AIController, generate_system_prompt
    from cli_agents.memory import ConversationMemory
    from openai import AsyncOpenAI

    config = load_env(project_root=SHARE)
    client = AsyncOpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )
    memory = ConversationMemory(
        system_prompt=generate_system_prompt(SHARE)
    )
    agent = AIController(client, config, memory)

    chunks: list[str] = []
    async for chunk in agent.handle_message(prompt):
        if not chunk.startswith("\x00"):
            chunks.append(chunk)

    return "".join(chunks)


def main() -> None:
    _log("SandboxCLIBridge starting")

    # Signal host that we are ready
    READY_FILE.write_text("ready", encoding="utf-8")
    _log(f"Ready sentinel written → {READY_FILE}")

    last_id: str | None = None

    while True:
        try:
            if CMD_FILE.exists():
                raw     = CMD_FILE.read_text(encoding="utf-8")
                payload = json.loads(raw)
                msg_id  = payload.get("id")
                prompt  = payload.get("prompt", "").strip()

                if msg_id and msg_id != last_id and prompt:
                    last_id = msg_id
                    _log(f"CMD [{msg_id}]: {prompt[:80]}")

                    try:
                        response = asyncio.run(_run_agent(prompt))
                    except Exception as exc:
                        response = f"[Sandbox agent error] {exc}"

                    _log(f"OUT [{msg_id}]: {response[:80]}")
                    OUT_FILE.write_text(
                        json.dumps({"id": msg_id, "response": response}),
                        encoding="utf-8",
                    )

        except (json.JSONDecodeError, OSError):
            pass

        time.sleep(POLL)


if __name__ == "__main__":
    main()