import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ────────────────────────────────────────────────────────────────
# CONFIG MODEL
# ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    openai_base_url: Optional[str]
    tavily_api_key: Optional[str]
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

    # 1. Load .env from project root
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # 2. Define standard paths
    dot_folder = project_root / ".cli_agents"
    settings_path = dot_folder / "settings.json"
    project_description_path = dot_folder / "CLI_AGENT.md"
    mcp_json_path = dot_folder / "mcp.config.json"

    # 3. Load JSON settings
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
    # 4. MCP CONFIG (Strict File Check)
    # ────────────────────────────────────────────────────────────
    # If the file exists in .cli_agents/, we use it. 
    # Otherwise, mcp_config_path is None, and AIController skips it.
    if mcp_json_path.exists():
        mcp_config_path = mcp_json_path.resolve()
    else:
        mcp_config_path = None

    # ────────────────────────────────────────────────────────────
    # 5. REQUIRED: OpenAI API Key
    # ────────────────────────────────────────────────────────────
    openai_api_key = (get("OPENAI_API_KEY") or "").strip()

    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Please set it in .env or .cli_agents/settings.json"
        )

    # ────────────────────────────────────────────────────────────
    # 6. Optional project instructions
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
    # 7. RETURN FINAL CONFIG
    # ────────────────────────────────────────────────────────────
    return AppConfig(
        openai_api_key=openai_api_key,
        openai_base_url=get("OPENAI_BASE_URL"),
        tavily_api_key=get("TAVILY_API_KEY"),
        model=get("MODEL", "openai/gpt-4o-mini"),
        project_root=project_root,
        project_instructions=project_instructions,
        mcp_config_path=mcp_config_path,
    )