from .fs_tools import (
    LIST_FOLDER_TOOL,
    READ_FILE_TOOL,
    SEARCH_PROJECT_TOOL,
    WRITE_FILE_TOOL,
    list_folder,
    read_file,
    search_project,
    write_file,
)
from .shell_tools import RUN_COMMAND_TOOL, run_shell_command
from .tavily import TAVILY_SEARCH_TOOL, tavily_search

TOOLS = [
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    LIST_FOLDER_TOOL,
    SEARCH_PROJECT_TOOL,
    RUN_COMMAND_TOOL,
    TAVILY_SEARCH_TOOL,
]

_EXECUTORS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_folder": list_folder,
    "search_project": search_project,
    "run_shell_command": run_shell_command,
    "tavily_search": tavily_search,
}


def execute_tool(name: str, args: dict) -> str:
    executor = _EXECUTORS.get(name)
    if executor is None:
        return f"Error: unknown tool '{name}'"

    try:
        return executor(**args)
    except TypeError as exc:
        return f"Error: invalid arguments for {name}: {exc}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"

__all__ = ["TOOLS", "execute_tool"]
