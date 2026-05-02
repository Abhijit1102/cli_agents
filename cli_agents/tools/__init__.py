import inspect

from .fs_tools import (
    ANALYZE_IMAGE_TOOL, LIST_FOLDER_TOOL, READ_FILE_TOOL,
    SEARCH_PROJECT_TOOL, WRITE_FILE_TOOL,
    analyze_image, list_folder, read_file, search_project, write_file,
)
from .shell_tools import RUN_COMMAND_TOOL, run_shell_command
from .tavily import TAVILY_SEARCH_TOOL, tavily_search

# ───────────────────────────────
# Tool Definitions (for LLM)
# ───────────────────────────────

TOOLS = [
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    LIST_FOLDER_TOOL,
    SEARCH_PROJECT_TOOL,
    ANALYZE_IMAGE_TOOL,
    RUN_COMMAND_TOOL,
    TAVILY_SEARCH_TOOL,
]

# ───────────────────────────────
# Tool Executors (actual functions)
# ───────────────────────────────

_EXECUTORS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_folder": list_folder,
    "search_project": search_project,
    "analyze_image": analyze_image,
    "run_shell_command": run_shell_command,
    "tavily_search": tavily_search,
}

# ───────────────────────────────
# Executor Engine (with DI)
# ───────────────────────────────

def execute_tool(name: str, args: dict, config=None) -> str:
    executor = _EXECUTORS.get(name)

    if executor is None:
        return f"Error: unknown tool '{name}'"

    try:
        sig = inspect.signature(executor)

        # ✅ Inject config automatically if required
        if "config" in sig.parameters:
            return executor(config=config, **args)

        return executor(**args)

    except TypeError as exc:
        return f"Error: invalid arguments for {name}: {exc}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"


__all__ = ["TOOLS", "execute_tool"]