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
        The schema is automatically derived from function type hints.
        """

        def wrapper(func: Callable):
            # 1. Extract type hints
            hints = get_type_hints(func)

            # 2. Build OpenAI parameters schema
            properties = {}
            required = []

            for param_name, param_type in hints.items():
                # Skip internal injection parameters and the return annotation
                if param_name in EXCLUDED_PARAMS:
                    continue

                properties[param_name] = {
                    "type": _python_type_to_openai(param_type),
                    "description": f"The {param_name} parameter.",
                }

                # Treat non-Optional hints as required
                is_optional = hasattr(param_type, "__origin__") and type(
                    None
                ) in getattr(param_type, "__args__", [])
                if not is_optional:
                    required.append(param_name)

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            # 3. Create a Pydantic model for runtime validation (strictly excluding 'return')
            field_definitions = {
                k: (v, ...) if k in required else (v, None)
                for k, v in hints.items()
                if k not in EXCLUDED_PARAMS
            }

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

    def get_openai_schemas(self) -> list[dict[str, Any]]:
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


# Global instance for use as a decorator
registry = ToolRegistry()
tool = registry.register
