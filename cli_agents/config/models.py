from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class AppConfig:
    """
    Application configuration model.
    Frozen to ensure immutability after loading.
    """
    openai_api_key: str
    openai_base_url: Optional[str]
    model: str
    project_root: Path
    project_instructions: Optional[str] = None
    mcp_config_path: Optional[Path] = None
    image_model: Optional[str] = None
