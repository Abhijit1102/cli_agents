import os
import shlex
import subprocess
from pathlib import Path

RUN_COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "run_shell_command",
        "description": "Run a shell command in the project environment.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute."},
                "cwd": {"type": "string", "description": "Working directory for the command."},
                "timeout": {"type": "integer", "description": "Timeout in seconds."},
            },
            "required": ["command"],
        },
    },
}


def run_shell_command(command: str, cwd: str | None = None, timeout: int = 30) -> str:
    if not command.strip():
        return "Error: command is empty."

    workdir = Path(cwd).resolve() if cwd else Path.cwd()
    if not workdir.exists():
        return f"Error: cwd does not exist: {workdir}"

    shell = os.name == "nt"
    try:
        result = subprocess.run(
            command,
            shell=shell,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout} seconds."
    except Exception as exc:
        return f"Error running command: {exc}"

    output = result.stdout.strip()
    error = result.stderr.strip()
    if result.returncode != 0:
        return f"Error ({result.returncode}): {error or output}"
    return output or "✔ Command completed successfully."
