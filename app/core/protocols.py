"""
Modern Protocol-based interfaces for the application.
Uses Python's Protocol for structural subtyping (duck typing with type safety).

Advantages over ABC:
- No inheritance required (structural subtyping)
- More Pythonic (duck typing)
- Better for composition over inheritance
- Easier testing and mocking
"""

from typing import (
    List, Optional, Dict, Any,
    AsyncIterator, Protocol, runtime_checkable
)
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from datetime import datetime

from app.models.schemas import InvestorProfile, SearchResult, ChatMessage


# ============================================================================
# Configuration Dataclasses
# ============================================================================

@dataclass(frozen=True)
class LLMConfig:
    """Immutable configuration for LLM providers."""
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderState:
    """Mutable state for providers."""
    initialized: bool = False
    last_used: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0


# ============================================================================
# Provider Protocols (Structural Subtyping)
# ============================================================================

@runtime_checkable
class LLMProvider(Protocol):
    """
    Protocol for Language Model providers.
    Any class implementing these methods is considered an LLMProvider.

    Usage:
        def use_llm(provider: LLMProvider):
            # Works with any class that has these methods
            response = await provider.generate_response(messages)
    """

    @property
    def name(self) -> str:
        """Provider name (e.g., 'gemini', 'openai')."""
        ...

    @property
    def config(self) -> LLMConfig:
        """Provider configuration."""
        ...

    async def generate_response(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response from the model."""
        ...

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the model."""
        ...


@runtime_checkable
class SearchProvider(Protocol):
    """Protocol for search providers."""

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform a search."""
        ...

    async def search_investors(
        self,
        sectors: List[str],
        location: Optional[str] = None,
        num_results: int = 10
    ) -> List[SearchResult]:
        """Search for investors."""
        ...


@runtime_checkable
class ScraperProvider(Protocol):
    """Protocol for web scraping providers."""

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def supported_domains(self) -> List[str]:
        """Domains this scraper can handle."""
        ...

    async def scrape_profile(self, url: str) -> Optional[InvestorProfile]:
        """Scrape a profile from URL."""
        ...

    async def enrich_profile(self, profile: InvestorProfile) -> InvestorProfile:
        """Enrich an existing profile with additional data."""
        ...


@runtime_checkable
class Initializable(Protocol):
    """Protocol for providers that need initialization."""

    async def initialize(self) -> None:
        """Initialize the provider."""
        ...

    async def cleanup(self) -> None:
        """Cleanup resources."""
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """Protocol for providers that support health checks."""

    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        ...


# ============================================================================
# Base Implementation Mixin (Optional helpers)
# ============================================================================

class ProviderMixin:
    """
    Mixin providing common functionality for providers.
    Use via composition, not inheritance.
    """

    def __init__(self):
        self._state = ProviderState()

    @property
    def state(self) -> ProviderState:
        return self._state

    @property
    def is_initialized(self) -> bool:
        return self._state.initialized

    def mark_initialized(self) -> None:
        self._state.initialized = True
        self._state.last_used = datetime.utcnow()

    def record_request(self) -> None:
        self._state.request_count += 1
        self._state.last_used = datetime.utcnow()

    def record_error(self) -> None:
        self._state.error_count += 1

    async def health_check(self) -> bool:
        return self._state.initialized


# ============================================================================
# Context Managers for Resource Management
# ============================================================================

@asynccontextmanager
async def managed_provider(provider: Initializable):
    """
    Async context manager for provider lifecycle.

    Usage:
        async with managed_provider(GeminiProvider(config)) as llm:
            response = await llm.generate_response(messages)
    """
    try:
        await provider.initialize()
        yield provider
    finally:
        await provider.cleanup()


# ============================================================================
# Type Aliases for Convenience
# ============================================================================

# Combined protocol for full-featured LLM provider
# Can extend: LLMProvider & Initializable & HealthCheckable
FullLLMProvider = LLMProvider
