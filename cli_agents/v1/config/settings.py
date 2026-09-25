from dataclasses import dataclass, field
from typing import Dict, Any
from cli_agents.config.models import AppConfig

@dataclass
class System1Config:
    """Configuration for the fast, reflexive path."""
    intent_threshold: float = 0.8
    enabled_heuristics: list[str] = field(default_factory=lambda: ["basic_commands", "file_ops"])

@dataclass
class V1Config:
    """Global configuration for the v1 architecture."""
    system1: System1Config = field(default_factory=System1Config)
    config: AppConfig = field(default_factory=lambda: AppConfig(
        openai_api_key="",
        openai_base_url=None,
        model="gpt-4o",
        project_root=None,
        jevai_api_key="",
        jevai_base_url=None,
        jevai_model="jev-ai"
    ))
    debug_mode: bool = False
