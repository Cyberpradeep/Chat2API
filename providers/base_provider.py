"""
Abstract Base Provider contract.
All providers (ChatGPT, and future Claude / Gemini) implement this unified interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseProvider(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initializes the browser session and connects to the service."""
        pass

    @abstractmethod
    async def send_prompt(
        self,
        prompt: str,
        think: bool = False,
        web_search: bool = False,
        deep_research: bool = False,
        files: Optional[List[str]] = None,
        new_chat: bool = False,
        timeout_seconds: int = 180
    ) -> Dict[str, Any]:
        """
        Sends a prompt with feature toggles and optional file attachments,
        and returns the structured response.
        """
        pass

    @abstractmethod
    async def new_chat(self) -> None:
        """Resets to a clean conversation session."""
        pass

    @abstractmethod
    async def is_ready(self) -> Dict[str, Any]:
        """Returns readiness status."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cleans up resources and closes browser."""
        pass
