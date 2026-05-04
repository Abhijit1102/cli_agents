import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    openai_base_url: Optional[str]
    tavily_api_key: Optional[str]
    model: str
    project_root: Path
    project_instructions: Optional[str] = None

def load_config(project_root: Path | None = None) -> AppConfig:
    project_root = Path(project_root or Path.cwd()).resolve()

    # 1. Load .env
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # 2. Load JSON config
    json_config = {}
    settings_path = project_root / ".cli_agents" / "settings.json"
    project_description_path = project_root / ".cli_agents" / "CLI_AGENT.md"

    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                json_config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Invalid settings.json: {e}")

    # 3. Helper
    def get(key: str, default: Optional[str] = None):
        return json_config.get(key) or os.getenv(key) or default

    # 4. Required key
    openai_api_key = (get("OPENAI_API_KEY") or "").strip()
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in settings.json, .env, or environment."
        )

    # ✅ 5. Optional project instructions
    project_instructions = None
    if project_description_path.exists():
        try:
            project_instructions = project_description_path.read_text(
                encoding="utf-8"
            ).strip()
        except Exception:
            project_instructions = None  # fail silently

    return AppConfig(
        openai_api_key=openai_api_key,
        openai_base_url=get("OPENAI_BASE_URL"),
        tavily_api_key=get("TAVILY_API_KEY"),
        model=get("MODEL", "openai/gpt-4o-mini"),
        project_root=project_root,
        project_instructions=project_instructions,  # 👈 PASS HERE
    )