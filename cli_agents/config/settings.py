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


def load_config(project_root: Path | None = None) -> AppConfig:
    project_root = Path(project_root or Path.cwd()).resolve()

    # 1. Load .env
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # 2. Load JSON config (user override)
    json_config = {}
    settings_path = project_root / ".cli_agents" / "settings.json"

    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                json_config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Invalid settings.json: {e}")

    # 3. Helper: JSON > ENV > default
    def get(key: str, default: Optional[str] = None):
        return json_config.get(key) or os.getenv(key) or default

    openai_api_key = (get("OPENAI_API_KEY") or "").strip()
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in settings.json, .env, or environment."
        )

    return AppConfig(
        openai_api_key=openai_api_key,
        openai_base_url=get("OPENAI_BASE_URL"),
        tavily_api_key=get("TAVILY_API_KEY"),
        model=get("MODEL", "openai/gpt-4o-mini"),
        project_root=project_root,
    )