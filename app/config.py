"""
Application configuration using Pydantic Settings.
Supports multiple environments and providers.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, Any
from functools import lru_cache
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Add new provider API keys here as the application grows.
    """

    # Application
    app_name: str = Field(default="AI Investor Finder", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    allowed_origins: str = Field(
        default="*",
        env="ALLOWED_ORIGINS",
        description="Comma-separated origins for CORS (use * for all)"
    )

    # LLM Providers
    # Gemini
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")

    # OpenAI (optional)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")

    # Anthropic (optional, for future use)
    anthropic_api_key: Optional[str] = Field(
        default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")

    # Default LLM Provider
    default_llm_provider: str = Field(
        default="gemini", env="DEFAULT_LLM_PROVIDER")

    # Search Providers
    google_search_api_key: str = Field(default="", env="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str = Field(
        default="", env="GOOGLE_SEARCH_ENGINE_ID")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=30, env="RATE_LIMIT_PER_MINUTE")

    # Search behavior
    search_timeout_seconds: int = Field(
        default=15, env="SEARCH_TIMEOUT_SECONDS")
    search_max_retries: int = Field(default=2, env="SEARCH_MAX_RETRIES")
    search_cache_ttl_minutes: int = Field(
        default=20, env="SEARCH_CACHE_TTL_MINUTES")

    # Scraping
    linkedin_scrape_delay: int = Field(default=2, env="LINKEDIN_SCRAPE_DELAY")
    linkedin_max_concurrency: int = Field(
        default=3, env="LINKEDIN_MAX_CONCURRENCY")
    scraping_timeout: int = Field(default=30, env="SCRAPING_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_json: bool = Field(default=False, env="LOG_JSON")

    # Memory & Persistence
    memory_persistence_enabled: bool = Field(
        default=True, env="MEMORY_PERSISTENCE_ENABLED")
    memory_persistence_path: str = Field(
        default="data/conversations", env="MEMORY_PERSISTENCE_PATH")
    conversation_max_ttl_hours: int = Field(
        default=24, env="CONVERSATION_MAX_TTL_HOURS")
    max_conversations: int = Field(default=1000, env="MAX_CONVERSATIONS")
    max_messages_per_conversation: int = Field(
        default=100, env="MAX_MESSAGES_PER_CONVERSATION")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/investor_finder.db",
        env="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific LLM provider."""
        configs = {
            "gemini": {
                "api_key": self.gemini_api_key,
                "model": self.gemini_model,
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            }
        }
        return configs.get(provider, {})

    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider has its API key configured."""
        config = self.get_llm_config(provider)
        return bool(config.get("api_key"))

    def parsed_allowed_origins(self) -> list[str]:
        """Return allowed origins for CORS as list."""
        raw = self.allowed_origins.strip()
        if not raw:
            return ["*"]
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        return origins or ["*"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_available_llm_providers() -> list:
    """Get list of configured LLM providers."""
    settings = get_settings()
    providers = []

    if settings.gemini_api_key:
        providers.append("gemini")
    if settings.openai_api_key:
        providers.append("openai")
    if settings.anthropic_api_key:
        providers.append("anthropic")

    return providers
