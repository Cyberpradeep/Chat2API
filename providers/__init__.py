from .base_provider import BaseProvider
from .chatgpt.provider import ChatGPTProvider

# Global provider instance
_default_provider = None

def get_provider(name: str = "chatgpt") -> BaseProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = ChatGPTProvider()
    return _default_provider

__all__ = ["BaseProvider", "ChatGPTProvider", "get_provider"]
