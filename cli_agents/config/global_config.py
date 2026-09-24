from typing import Optional
from .models import AppConfig

_config: Optional[AppConfig] = None

def set_config(config: AppConfig):
    """Sets the global application configuration."""
    global _config
    _config = config

def get_config() -> AppConfig:
    """
    Retrieves the global application configuration.
    Raises RuntimeError if the config has not been initialized.
    """
    if _config is None:
        raise RuntimeError("Config not initialized. Call set_config() first.")
    return _config
