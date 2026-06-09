from .config import load_config, resolve_model
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from .protocol import LLMMessage, LLMProvider, ToolCall

_REGISTRY: dict[str, type] = {
    "ollama": OllamaProvider,
    "openrouter": OpenRouterProvider,
}


def get_provider(name: str) -> OllamaProvider | OpenRouterProvider:
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY)
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    return _REGISTRY[name]()


__all__ = [
    "LLMMessage",
    "LLMProvider",
    "ToolCall",
    "load_config",
    "resolve_model",
    "get_provider",
    "OllamaProvider",
    "OpenRouterProvider",
]
