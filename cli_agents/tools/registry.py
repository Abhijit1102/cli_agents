import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from pydantic import create_model

# ────────────────────────────────────────────────────────────────
# TYPE MAPPING FOR OPENAI
# ────────────────────────────────────────────────────────────────
# Maps Python types to OpenAI JSON Schema types
TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

# Parameter names that should never be treated as tool input arguments
EXCLUDED_PARAMS = {"config", "return"}


def _python_type_to_openai(py_type: Any) -> str:
    """Recursively resolve Python types to OpenAI JSON schema types."""
    # Handle Optional[T] (which is Union[T, None])
    if hasattr(py_type, "__origin__") and py_type.__origin__ is not None:
        if py_type.__origin__ == list:
            return "array"
        # For Optional/Union, take the first non-None type
        args = getattr(py_type, "__args__", [])
        for arg in args:
            if arg is not type(None):
                return _python_type_to_openai(arg)

    return TYPE_MAP.get(py_type, "string")


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable
    model: type  # Pydantic model for validation


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str):
        """
        Decorator to register a function as a tool.
        The schema is automatically derived from function type hints and defaults.
        """

        def wrapper(func: Callable):
            # 1. Extract type hints and signature defaults
            hints = get_type_hints(func)
            sig = inspect.signature(func)

            # 2. Build OpenAI parameters schema
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Skip internal injection parameters
                if param_name in EXCLUDED_PARAMS:
                    continue

                param_type = hints.get(param_name, Any)
                properties[param_name] = {
                    "type": _python_type_to_openai(param_type),
                    "description": f"The {param_name} parameter.",
                }

                # A parameter is optional if it has a default value OR is typed as Optional
                has_default = param.default is not inspect.Parameter.empty
                is_optional_type = hasattr(param_type, "__origin__") and type(
                    None
                ) in getattr(param_type, "__args__", [])
                
                if not (has_default or is_optional_type):
                    required.append(param_name)

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            # 3. Create a Pydantic model for runtime validation
            field_definitions = {}
            for param_name, param in sig.parameters.items():
                if param_name in EXCLUDED_PARAMS:
                    continue
                
                param_type = hints.get(param_name, Any)
                default = param.default if param.default is not inspect.Parameter.empty else ...
                
                # If it's in required list, we use ..., otherwise we use the default
                if param_name in required:
                    field_definitions[param_name] = (param_type, ...)
                else:
                    field_definitions[param_name] = (param_type, default)

            validation_model = create_model(f"{name}Model", **field_definitions)

            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                func=func,
                model=validation_model,
            )
            return func
        return wrapper

    def get_openai_schemas(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def get_definition(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

# Create a global instance for the project
registry = ToolRegistry()

# Alias the register method as 'tool' for the decorator usage: @tool(...)
tool = registry.register
