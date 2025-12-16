"""
Unit tests for ChatService.
"""

from app.services.chat_service import ChatService
import sys
from pathlib import Path
import pytest

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestChatServiceSectorExtraction:
    """Tests for sector keyword extraction."""

    def setup_method(self):
        """Set up test instance."""
        self.service = ChatService.__new__(ChatService)
        # Set class attributes without full initialization
        self.service.SECTOR_KEYWORDS = ChatService.SECTOR_KEYWORDS
        self.service.SEARCH_TRIGGERS = ChatService.SEARCH_TRIGGERS
        self.service.MORE_INVESTORS_TRIGGERS = ChatService.MORE_INVESTORS_TRIGGERS

    def test_extract_sectors_ai(self):
        """Test AI sector extraction."""
        sectors = self.service._extract_sectors(
            "Find me AI and machine learning investors")
        assert "ai" in sectors

    def test_extract_sectors_healthcare(self):
        """Test healthcare sector extraction."""
        sectors = self.service._extract_sectors(
            "I'm building a healthcare startup")
        assert "healthcare" in sectors

    def test_extract_sectors_fintech(self):
        """Test fintech sector extraction."""
        sectors = self.service._extract_sectors(
            "Looking for fintech and blockchain investors")
        assert "fintech" in sectors

    def test_extract_sectors_multiple(self):
        """Test multiple sector extraction."""
        sectors = self.service._extract_sectors(
            "AI healthcare fintech startup")
        assert len(sectors) >= 3
        assert "ai" in sectors
        assert "healthcare" in sectors
        assert "fintech" in sectors

    def test_extract_sectors_turkish(self):
        """Test Turkish keyword extraction."""
        sectors = self.service._extract_sectors(
            "Yapay zeka ve sağlık alanında yatırımcı arıyorum")
        assert "ai" in sectors or "healthcare" in sectors

    def test_extract_sectors_default(self):
        """Test default sectors when no match found."""
        sectors = self.service._extract_sectors("Just a random message")
        assert "startup" in sectors or "technology" in sectors

    def test_extract_sectors_empty(self):
        """Test with empty message."""
        sectors = self.service._extract_sectors("")
        assert "startup" in sectors or "technology" in sectors


class TestChatServiceSearchTriggers:
    """Tests for investor search trigger detection."""

    def setup_method(self):
        """Set up test instance."""
        self.service = ChatService.__new__(ChatService)
        self.service.SECTOR_KEYWORDS = ChatService.SECTOR_KEYWORDS
        self.service.SEARCH_TRIGGERS = ChatService.SEARCH_TRIGGERS
        self.service.MORE_INVESTORS_TRIGGERS = ChatService.MORE_INVESTORS_TRIGGERS

    def test_should_search_find_investor(self):
        """Test 'find investor' trigger."""
        assert self.service._should_search_investors(
            "Find me investors for my AI startup")

    def test_should_search_looking_for(self):
        """Test 'looking for' trigger."""
        assert self.service._should_search_investors(
            "Looking for VCs in healthcare")

    def test_should_search_vc(self):
        """Test 'VC' trigger."""
        assert self.service._should_search_investors("I need VC funding")

    def test_should_search_turkish(self):
        """Test Turkish trigger."""
        assert self.service._should_search_investors("Yatırımcı arıyorum")

    def test_should_not_search_greeting(self):
        """Test no trigger for casual conversation."""
        assert not self.service._should_search_investors("Hello, how are you?")

    def test_should_not_search_pagination(self):
        """Test that pagination requests don't trigger new search."""
        # Pagination should NOT trigger a new search
        result = self.service._is_pagination_request("show more investors")
        assert result is True
        # And _should_search_investors should return False for pagination
        assert not self.service._should_search_investors("show more investors")


class TestChatServicePagination:
    """Tests for pagination request detection."""

    def setup_method(self):
        """Set up test instance."""
        self.service = ChatService.__new__(ChatService)
        self.service.MORE_INVESTORS_TRIGGERS = ChatService.MORE_INVESTORS_TRIGGERS

    def test_is_pagination_more(self):
        """Test 'more' pagination trigger."""
        assert self.service._is_pagination_request("more")

    def test_is_pagination_show_more(self):
        """Test 'show more' pagination trigger."""
        assert self.service._is_pagination_request("show more investors")

    def test_is_pagination_next(self):
        """Test 'next' pagination trigger."""
        assert self.service._is_pagination_request("next")

    def test_is_pagination_continue(self):
        """Test 'continue' pagination trigger."""
        assert self.service._is_pagination_request("continue")

    def test_is_not_pagination(self):
        """Test non-pagination message."""
        assert not self.service._is_pagination_request("Find me AI investors")


class TestChatServiceLocationExtraction:
    """Tests for location extraction."""

    def setup_method(self):
        """Set up test instance."""
        self.service = ChatService.__new__(ChatService)

    def test_extract_location_silicon_valley(self):
        """Test Silicon Valley extraction."""
        loc = self.service._extract_location(
            "Find investors in Silicon Valley")
        assert loc is not None
        assert "silicon valley" in loc.lower()

    def test_extract_location_nyc(self):
        """Test NYC extraction."""
        loc = self.service._extract_location("Looking for VCs in NYC")
        assert loc == "NYC"

    def test_extract_location_new_york(self):
        """Test New York extraction."""
        loc = self.service._extract_location("Find investors in new york")
        assert loc is not None
        assert "new york" in loc.lower() or loc == "New York"

    def test_extract_location_from_pattern(self):
        """Test 'in <city>' pattern extraction."""
        loc = self.service._extract_location("Looking for investors in Boston")
        assert loc is not None
        assert "boston" in loc.lower()

    def test_extract_location_none(self):
        """Test no location found."""
        loc = self.service._extract_location("Find AI investors")
        assert loc is None


class TestChatServiceListProviders:
    """Tests for provider listing."""

    def test_list_available_providers(self):
        """Test listing available providers."""
        providers = ChatService.list_available_providers()

        assert "llm" in providers
        assert "search" in providers
        assert "scraper" in providers

        # LLM providers should include gemini
        assert isinstance(providers["llm"], list)
