import os
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


def load_env(project_root: Path | None = None) -> AppConfig:
    project_root = Path(project_root or Path.cwd()).resolve()
    env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in .env or in your environment."
        )

    return AppConfig(
        openai_api_key=openai_api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip() or None,
        model=os.getenv("MODEL", "openai/gpt-4o-mini"),
        project_root=project_root,
    )