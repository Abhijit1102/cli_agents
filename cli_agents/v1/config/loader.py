import os
import json
from pathlib import Path
from cli_agents.v1.config.settings import V1Config
from cli_agents.config.models import AppConfig

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def load_config() -> V1Config:
    """
    Loads configuration from .cli_agents/env.json and environment variables.
    """
    config = V1Config()
    root = Path.cwd().resolve()
    env_path = root / ".cli_agents" / "env.json"
    env_data = _load_json(env_path)
    
    project_root = Path(os.getenv("PROJECT_ROOT", root)).absolute()

    def get_val(key: str, default: str = None) -> str:
        return env_data.get(key) or os.getenv(key) or default

    # Unified AppConfig containing both System 2 (standard) and System 1 (Jev AI) settings
    config.config = AppConfig(
        # System 2: Standard LLM
        openai_api_key=get_val("OPENAI_API_KEY", "1a09d7627353434e9e693fd85103a3e7"),
        openai_base_url=get_val("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        model=get_val("MODEL", "gemma4:31b-cloud"),
        
        # System 1: Jev AI - Pulling from the same env.json or JEV_ prefixed vars
        jevai_api_key=get_val("JEV_OPENAI_API_KEY", get_val("OPENAI_API_KEY", "1a09d7627353434e9e693fd85103a3e7")),
        jevai_base_url=get_val("JEV_OPENAI_BASE_URL", get_val("OPENAI_BASE_URL", "http://localhost:11434/v1")),
        jevai_model=get_val("JEV_MODEL", "jev-ai"),
        
        project_root=project_root,
        project_instructions=get_val("PROJECT_INSTRUCTIONS"),
        mcp_config_path=Path(".cli_agents/mcp.config.json") if (root / ".cli_agents" / "mcp.config.json").exists() else None,
        image_model=get_val("IMAGE_MODEL")
    )

    return config
