"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.models import InvestorProfile, SearchResult, ChatMessage, MessageRole


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_investor() -> InvestorProfile:
    """Create a sample investor profile for testing."""
    return InvestorProfile(
        name="John Doe",
        title="Partner",
        company="Acme Ventures",
        email="john@acmevc.com",
        linkedin_url="https://linkedin.com/in/johndoe",
        location="San Francisco, CA",
        bio="Experienced VC partner with focus on early-stage startups.",
        investment_focus=["ai", "healthcare", "fintech"],
        source="linkedin"
    )


@pytest.fixture
def sample_investors() -> List[InvestorProfile]:
    """Create a list of sample investors for testing."""
    return [
        InvestorProfile(
            name="John Doe",
            title="Partner",
            company="Acme Ventures",
            email="john@acmevc.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            location="San Francisco, CA",
            investment_focus=["ai", "healthcare"],
            source="linkedin"
        ),
        InvestorProfile(
            name="Jane Smith",
            title="Managing Director",
            company="Tech Capital",
            email="jane@techcapital.com",
            linkedin_url="https://linkedin.com/in/janesmith",
            location="New York, NY",
            investment_focus=["saas", "fintech"],
            source="linkedin"
        ),
        InvestorProfile(
            name="Bob Johnson",
            title="General Partner",
            company="Innovation Fund",
            email="bob@innovationfund.com",
            linkedin_url="https://linkedin.com/in/bobjohnson",
            location="Boston, MA",
            investment_focus=["healthcare", "biotech"],
            source="web_search"
        ),
    ]


@pytest.fixture
def sample_search_result() -> SearchResult:
    """Create a sample search result for testing."""
    return SearchResult(
        title="John Doe - Partner at Acme Ventures | LinkedIn",
        url="https://linkedin.com/in/johndoe",
        snippet="John Doe is a Partner at Acme Ventures focused on AI and healthcare investments.",
        relevance_score=0.95
    )


@pytest.fixture
def sample_search_results() -> List[SearchResult]:
    """Create a list of sample search results for testing."""
    return [
        SearchResult(
            title="John Doe - Partner at Acme Ventures | LinkedIn",
            url="https://linkedin.com/in/johndoe",
            snippet="John Doe is a Partner at Acme Ventures focused on AI and healthcare investments.",
            relevance_score=0.95
        ),
        SearchResult(
            title="Jane Smith - Managing Director at Tech Capital | LinkedIn",
            url="https://linkedin.com/in/janesmith",
            snippet="Jane Smith leads investments in SaaS and fintech at Tech Capital.",
            relevance_score=0.90
        ),
    ]


@pytest.fixture
def sample_chat_message() -> ChatMessage:
    """Create a sample chat message for testing."""
    return ChatMessage(
        role=MessageRole.USER,
        content="Find me AI investors in Silicon Valley"
    )


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from app.main import app
    return TestClient(app)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.gemini_api_key = "test-api-key"
    settings.openai_api_key = None
    settings.anthropic_api_key = None
    settings.google_search_api_key = "test-search-key"
    settings.google_search_engine_id = "test-engine-id"
    settings.default_llm_provider = "gemini"
    settings.rate_limit_per_minute = 30
    settings.search_timeout_seconds = 15
    settings.search_max_retries = 2
    settings.search_cache_ttl_minutes = 20
    settings.linkedin_scrape_delay = 2
    settings.linkedin_max_concurrency = 3
    settings.linkedin_min_delay = 1.5
    settings.linkedin_max_delay = 4.0
    settings.max_conversations = 1000
    settings.max_messages_per_conversation = 100
    settings.conversation_max_ttl_hours = 24
    settings.memory_persistence_enabled = False
    settings.memory_persistence_path = None
    settings.llm_fallback_order = "gemini,openai,anthropic"
    settings.provider_failure_cooldown_seconds = 300
    settings.is_provider_configured = lambda p: p == "gemini"
    settings.parsed_allowed_origins = lambda: ["*"]
    return settings


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock()
    provider.name = "gemini"
    provider.generate_response = AsyncMock(return_value="This is a test response.")
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["This ", "is ", "a ", "test."]:
            yield chunk
    
    provider.generate_stream = mock_stream
    return provider
