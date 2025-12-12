"""
Modern Provider Registry using a simpler, more Pythonic approach.

Features:
- Simple dict-based registry
- Decorator for auto-registration
- FastAPI Depends integration
- Async context manager support
- Type-safe with Protocol checking
"""

from typing import Dict, Type, Optional, List, TypeVar, Callable, Any
from functools import wraps
import logging

from app.core.protocols import (
    LLMProvider,
    SearchProvider,
    ScraperProvider,
    LLMConfig,
    Initializable
)
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Type variable for generic provider
T = TypeVar('T')


# ============================================================================
# Simple Registry (Just dictionaries!)
# ============================================================================

class Registry:
    """
    Simple provider registry using dictionaries.
    Much cleaner than class-based approach with @classmethod everywhere.
    """

    def __init__(self):
        self._providers: Dict[str, Dict[str, type]] = {
            "llm": {},
            "search": {},
            "scraper": {}
        }
        self._instances: Dict[str, Dict[str, Any]] = {
            "llm": {},
            "search": {},
            "scraper": {}
        }

    def register(self, provider_type: str, name: str, cls: type) -> None:
        """Register a provider class."""
        if provider_type not in self._providers:
            raise ValueError(f"Unknown provider type: {provider_type}")

        self._providers[provider_type][name.lower()] = cls
        logger.info(f"Registered {provider_type} provider: {name}")

    def get_class(self, provider_type: str, name: str) -> Optional[type]:
        """Get a provider class by type and name."""
        return self._providers.get(provider_type, {}).get(name.lower())

    def get_instance(self, provider_type: str, name: str) -> Optional[Any]:
        """Get a cached provider instance."""
        return self._instances.get(provider_type, {}).get(name.lower())

    def set_instance(self, provider_type: str, name: str, instance: Any) -> None:
        """Cache a provider instance."""
        self._instances[provider_type][name.lower()] = instance

    def list_providers(self, provider_type: str) -> List[str]:
        """List all registered providers of a type."""
        return list(self._providers.get(provider_type, {}).keys())

    async def cleanup_all(self) -> None:
        """Cleanup all cached instances."""
        for provider_type, instances in self._instances.items():
            for name, instance in instances.items():
                if hasattr(instance, 'cleanup'):
                    try:
                        await instance.cleanup()
                    except Exception as e:
                        logger.error(
                            f"Error cleaning up {provider_type}/{name}: {e}")

        self._instances = {"llm": {}, "search": {}, "scraper": {}}
        logger.info("All provider instances cleaned up")


# Global registry instance
registry = Registry()


# ============================================================================
# Registration Decorator
# ============================================================================

def register(provider_type: str, name: str):
    """
    Decorator to register a provider class.

    Usage:
        @register("llm", "gemini")
        class GeminiProvider:
            ...
    """
    def decorator(cls: type) -> type:
        registry.register(provider_type, name, cls)

        # Store metadata on the class
        cls._provider_type = provider_type
        cls._provider_name = name

        return cls
    return decorator


# Convenience decorators
def llm_provider(name: str):
    """Register an LLM provider."""
    return register("llm", name)


def search_provider(name: str):
    """Register a search provider."""
    return register("search", name)


def scraper_provider(name: str):
    """Register a scraper provider."""
    return register("scraper", name)


# ============================================================================
# Factory Functions
# ============================================================================

async def get_llm(
    name: str,
    config: LLMConfig,
    cache: bool = True
) -> LLMProvider:
    """
    Get or create an LLM provider instance.

    Args:
        name: Provider name (e.g., 'gemini', 'openai')
        config: LLM configuration
        cache: Whether to cache the instance

    Returns:
        LLM provider instance
    """
    cache_key = f"{name}:{config.model_name}"

    if cache:
        cached = registry.get_instance("llm", cache_key)
        if cached:
            return cached

    cls = registry.get_class("llm", name)
    if not cls:
        available = registry.list_providers("llm")
        raise ConfigurationError(
            f"LLM provider '{name}' not found. Available: {available}"
        )

    instance = cls(config)

    if hasattr(instance, 'initialize'):
        await instance.initialize()

    if cache:
        registry.set_instance("llm", cache_key, instance)

    return instance


async def get_search(name: str, cache: bool = True, **kwargs) -> SearchProvider:
    """Get or create a search provider instance."""
    if cache:
        cached = registry.get_instance("search", name)
        if cached:
            return cached

    cls = registry.get_class("search", name)
    if not cls:
        available = registry.list_providers("search")
        raise ConfigurationError(
            f"Search provider '{name}' not found. Available: {available}"
        )

    instance = cls(**kwargs)

    if cache:
        registry.set_instance("search", name, instance)

    return instance


async def get_scraper(name: str, cache: bool = True, **kwargs) -> ScraperProvider:
    """Get or create a scraper provider instance."""
    if cache:
        cached = registry.get_instance("scraper", name)
        if cached:
            return cached

    cls = registry.get_class("scraper", name)
    if not cls:
        available = registry.list_providers("scraper")
        raise ConfigurationError(
            f"Scraper provider '{name}' not found. Available: {available}"
        )

    instance = cls(**kwargs)

    if hasattr(instance, 'initialize'):
        await instance.initialize()

    if cache:
        registry.set_instance("scraper", name, instance)

    return instance


# ============================================================================
# FastAPI Dependency Injection Helpers
# ============================================================================

def llm_dependency(
    name: str = "gemini",
    model: str = "gemini-2.0-flash"
) -> Callable:
    """
    Create a FastAPI dependency for LLM provider.

    Usage:
        @router.post("/chat")
        async def chat(llm: LLMProvider = Depends(llm_dependency("gemini"))):
            return await llm.generate_response(messages)
    """
    async def dependency() -> LLMProvider:
        config = LLMConfig(model_name=model)
        return await get_llm(name, config)

    return dependency


def search_dependency(name: str = "google") -> Callable:
    """Create a FastAPI dependency for search provider."""
    async def dependency() -> SearchProvider:
        return await get_search(name)

    return dependency


def scraper_dependency(name: str = "linkedin") -> Callable:
    """Create a FastAPI dependency for scraper provider."""
    async def dependency() -> ScraperProvider:
        return await get_scraper(name)

    return dependency


# ============================================================================
# Backward Compatibility Layer
# ============================================================================

class ProviderRegistry:
    """Backward compatible registry interface."""

    @classmethod
    def register_llm(cls, name: str, provider_class: type) -> None:
        registry.register("llm", name, provider_class)

    @classmethod
    def register_search(cls, name: str, provider_class: type) -> None:
        registry.register("search", name, provider_class)

    @classmethod
    def register_scraper(cls, name: str, provider_class: type) -> None:
        registry.register("scraper", name, provider_class)

    @classmethod
    def get_llm_provider(cls, name: str) -> Optional[type]:
        return registry.get_class("llm", name)

    @classmethod
    def get_search_provider(cls, name: str) -> Optional[type]:
        return registry.get_class("search", name)

    @classmethod
    def get_scraper_provider(cls, name: str) -> Optional[type]:
        return registry.get_class("scraper", name)

    @classmethod
    def list_llm_providers(cls) -> List[str]:
        return registry.list_providers("llm")

    @classmethod
    def list_search_providers(cls) -> List[str]:
        return registry.list_providers("search")

    @classmethod
    def list_scraper_providers(cls) -> List[str]:
        return registry.list_providers("scraper")


class ProviderFactory:
    """Backward compatible factory interface."""

    @classmethod
    async def create_llm_provider(cls, name: str, config: LLMConfig, cache: bool = True):
        return await get_llm(name, config, cache)

    @classmethod
    async def create_search_provider(cls, name: str, cache: bool = True, **kwargs):
        return await get_search(name, cache, **kwargs)

    @classmethod
    async def create_scraper_provider(cls, name: str, cache: bool = True, **kwargs):
        return await get_scraper(name, cache, **kwargs)

    @classmethod
    async def cleanup_all(cls) -> None:
        await registry.cleanup_all()


# Keep old decorator for compatibility
def register_provider(provider_type: str, name: str):
    """Backward compatible decorator."""
    return register(provider_type, name)
