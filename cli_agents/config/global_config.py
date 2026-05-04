from typing import Optional
from .settings import AppConfig

_config: Optional[AppConfig] = None


def set_config(config: AppConfig):
    global _config
    _config = config


def get_config() -> AppConfig:
    if _config is None:
        raise RuntimeError("Config not initialized. Call set_config() first.")
    return _config