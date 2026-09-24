import os
import json
from pathlib import Path
from typing import Optional, Any, Dict
from .models import AppConfig

def load_config(project_root: Path | None = None) -> AppConfig:
    """
    Loads configuration from multiple sources with the following priority:
    1. settings.json (Explicit overrides)
    2. env.json (Project-specific env)
    3. System Environment Variables
    4. Default values
    """
    root = Path(project_root or Path.cwd()).resolve()
    dot_folder = root / ".cli_agents"
    
    # Paths to config files
    paths = {
        "env": dot_folder / "env.json",
        "settings": dot_folder / "settings.json",
        "instructions": dot_folder / "CLI_AGENT.md",
        "mcp": dot_folder / "mcp.config.json",
    }

    # Load JSON files
    env_data = _load_json(paths["env"])
    settings_data = _load_json(paths["settings"])

    def get_value(key: str, default: Any = None) -> Any:
        # Priority: settings.json -> env.json -> Environment Variable -> Default
        return settings_data.get(key) or env_data.get(key) or os.getenv(key) or default

    # Validation for required key
    api_key = (get_value("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            f"OPENAI_API_KEY is missing. Please set it in {paths['env']}, "
            f"{paths['settings']}, or as an environment variable."
        )

    # Resolve optional project instructions
    instructions = None
    if paths["instructions"].exists():
        try:
            instructions = paths["instructions"].read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Resolve MCP config path
    mcp_path = paths["mcp"].resolve() if paths["mcp"].exists() else None

    return AppConfig(
        openai_api_key=api_key,
        openai_base_url=get_value("OPENAI_BASE_URL"),
        model=get_value("MODEL", "openai/gpt-4o-mini"),
        project_root=root,
        project_instructions=instructions,
        mcp_config_path=mcp_path,
        image_model=get_value("IMAGE_MODEL"),
    )

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, Exception) as e:
        # We log or raise depending on how strict we want to be. 
        # For config, usually a failure to parse a present file should be an error.
        raise RuntimeError(f"Failed to parse {path}: {e}")
