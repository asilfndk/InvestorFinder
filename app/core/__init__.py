"""
Core module containing protocols, providers, and shared components.
Uses modern Protocol-based architecture for type-safe provider management.
"""

# Events
from app.core.events import EventBus, Event, EventType, event_bus

# Exceptions
from app.core.exceptions import (
    AppException,
    LLMProviderError,
    SearchProviderError,
    ScraperError,
    ConfigurationError,
)

# Protocols (type definitions)
from app.core.protocols import (
    LLMProvider,
    SearchProvider,
    ScraperProvider,
    LLMConfig,
    ProviderState,
    ProviderMixin,
    managed_provider,
)

# Registry and factory functions
from app.core.providers import (
    registry,
    register,
    llm_provider,
    search_provider,
    scraper_provider,
    get_llm,
    get_search,
    get_scraper,
    llm_dependency,
    search_dependency,
    scraper_dependency,
)

__all__ = [
    # Protocols
    "LLMProvider",
    "SearchProvider",
    "ScraperProvider",
    "LLMConfig",
    "ProviderState",
    "ProviderMixin",
    "managed_provider",
    # Registry
    "registry",
    "register",
    "llm_provider",
    "search_provider",
    "scraper_provider",
    "get_llm",
    "get_search",
    "get_scraper",
    "llm_dependency",
    "search_dependency",
    "scraper_dependency",
    # Exceptions
    "AppException",
    "LLMProviderError",
    "SearchProviderError",
    "ScraperError",
    "ConfigurationError",
    # Events
    "EventBus",
    "Event",
    "EventType",
    "event_bus",
]
