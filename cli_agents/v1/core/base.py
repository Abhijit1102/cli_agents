from abc import ABC, abstractmethod
from typing import Any

class BaseProcess(ABC):
    """Base class for all AI processing units (System 1, System 2, etc.)"""
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass
