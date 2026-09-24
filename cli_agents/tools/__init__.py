import inspect
import importlib
import pkgutil
from pydantic import ValidationError
from .registry import registry

# ───────────────────────────────
# Dynamic Tool Loading
# ───────────────────────────────

for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    if module_name != "registry":
        importlib.import_module(f".{module_name}", package="cli_agents.tools")

TOOLS = registry.get_openai_schemas()

# ───────────────────────────────
# Executor Engine (with Validation & DI)
# ───────────────────────────────

def execute_tool(name: str, args: dict, config=None) -> str:
    tool_def = registry.get_definition(name)

    if tool_def is None:
        return f"Error: unknown tool '{name}'"

    try:
        # 1. Pydantic Validation
        # This ensures that inputs are converted to correct types (e.g. "10" -> 10)
        # and raises ValidationError if required fields are missing.
        validated_args = tool_def.model(**args).model_dump()

        # 2. Signature-based Injection
        sig = inspect.signature(tool_def.func)
        
        # Inject config if the function asks for it
        if "config" in sig.parameters:
            return tool_def.func(config=config, **validated_args)

        return tool_def.func(**validated_args)

    except ValidationError as exc:
        return f"Error: invalid arguments for {name}. {exc}"
    except TypeError as exc:
        return f"Error: argument mismatch for {name}: {exc}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"


__all__ = ["TOOLS", "execute_tool"]
