import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────
# CONFIG MODEL
# ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    openai_base_url: Optional[str]
    model: str
    project_root: Path
    project_instructions: Optional[str] = None
    mcp_config_path: Optional[Path] = None


# ────────────────────────────────────────────────────────────────
# LOAD CONFIG
# ────────────────────────────────────────────────────────────────
def load_config(project_root: Path | None = None) -> AppConfig:
    """
    Loads configuration with a strict check for MCP config:
    If .cli_agents/mcp.config.json exists, it is used. Otherwise, None.
    """
    project_root = Path(project_root or Path.cwd()).resolve()

    # 1. Define standard paths
    dot_folder = project_root / ".cli_agents"
    env_json_path = dot_folder / "env.json"
    settings_path = dot_folder / "settings.json"
    project_description_path = dot_folder / "CLI_AGENT.md"
    mcp_json_path = dot_folder / "mcp.config.json"

    # Load the JSON project configuration without overriding environment values.
    env_config = {}
    if env_json_path.exists():
        try:
            with open(env_json_path, "r", encoding="utf-8") as f:
                env_config = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid env.json: {e}")

        if not isinstance(env_config, dict):
            raise RuntimeError("Invalid env.json: expected a JSON object")

        for key, value in env_config.items():
            if value is not None:
                os.environ.setdefault(key, str(value))

    # 2. Load JSON settings
    json_config = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                json_config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Invalid settings.json: {e}")

    # Helper to get config from JSON first, then Environment
    def get(key: str, default: Optional[str] = None):
        return json_config.get(key) or os.getenv(key) or default

    # ────────────────────────────────────────────────────────────
    # 3. MCP CONFIG (Strict File Check)
    # ────────────────────────────────────────────────────────────
    # If the file exists in .cli_agents/, we use it. 
    # Otherwise, mcp_config_path is None, and AIController skips it.
    if mcp_json_path.exists():
        mcp_config_path = mcp_json_path.resolve()
    else:
        mcp_config_path = None

    # ────────────────────────────────────────────────────────────
    # 4. REQUIRED: OpenAI API Key
    # ────────────────────────────────────────────────────────────
    openai_api_key = (
        env_config.get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Please set it in "
            f"{env_json_path} or {settings_path}, or set it in the environment."
        )

    # ────────────────────────────────────────────────────────────
    # 5. Optional project instructions
    # ────────────────────────────────────────────────────────────
    project_instructions = None
    if project_description_path.exists():
        try:
            project_instructions = project_description_path.read_text(
                encoding="utf-8"
            ).strip()
        except Exception:
            project_instructions = None

    # ────────────────────────────────────────────────────────────
    # 6. RETURN FINAL CONFIG
    # ────────────────────────────────────────────────────────────
    return AppConfig(
        openai_api_key=openai_api_key,
        openai_base_url=get("OPENAI_BASE_URL"),
        model=get("MODEL", "openai/gpt-4o-mini"),
        project_root=project_root,
        project_instructions=project_instructions,
        mcp_config_path=mcp_config_path,
    )