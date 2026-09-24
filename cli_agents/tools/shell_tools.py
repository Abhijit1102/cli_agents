import os
import subprocess
from pathlib import Path
from .registry import tool

@tool(
    name="run_shell_command",
    description="Run a shell command in the project environment. Returns stdout and stderr separately.",
)
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

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    
    output_parts = [f"Exit Code: {result.returncode}"]
    
    if stdout:
        output_parts.append(f"\nSTDOUT:\n{stdout}")
    
    if stderr:
        output_parts.append(f"\nSTDERR:\n{stderr}")
        
    if not stdout and not stderr and result.returncode == 0:
        return "✔ Command completed successfully (no output)."
        
    return "\n".join(output_parts)
