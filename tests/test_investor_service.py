"""
Unit tests for InvestorService.
"""

from app.models import InvestorProfile
from app.services.investor_service import InvestorService
import sys
from pathlib import Path
import pytest

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestInvestorServiceCacheKey:
    """Tests for cache key generation."""

    def setup_method(self):
        """Set up test instance."""
        self.service = InvestorService.__new__(InvestorService)

    def test_cache_key_single_sector(self):
        """Test cache key with single sector."""
        key = self.service._cache_key(["ai"], "United States", 10)
        assert key == "ai|united states|10"

    def test_cache_key_multiple_sectors(self):
        """Test cache key with multiple sectors (sorted)."""
        key = self.service._cache_key(
            ["healthcare", "ai", "fintech"], "New York", 20)
        # Sectors should be sorted alphabetically
        assert key == "ai,fintech,healthcare|new york|20"

    def test_cache_key_case_insensitive(self):
        """Test cache key is case insensitive."""
        key1 = self.service._cache_key(["AI", "Healthcare"], "NYC", 10)
        key2 = self.service._cache_key(["ai", "healthcare"], "nyc", 10)
        assert key1 == key2


class TestInvestorServicePagination:
    """Tests for pagination functionality."""

    def setup_method(self):
        """Set up test instance with sample investors."""
        self.service = InvestorService.__new__(InvestorService)
        # Create sample investors
        self.service._all_investors = [
            InvestorProfile(name=f"Investor {i}", source="test")
            for i in range(25)
        ]
        self.service._current_page = 0
        self.service._page_size = 10

    def test_get_first_page(self):
        """Test getting first page of investors."""
        investors, total, has_more = self.service.get_paginated_investors(
            page=0, page_size=10)

        assert len(investors) == 10
        assert total == 25
        assert has_more is True
        assert investors[0].name == "Investor 0"
        assert investors[9].name == "Investor 9"

    def test_get_second_page(self):
        """Test getting second page."""
        investors, total, has_more = self.service.get_paginated_investors(
            page=1, page_size=10)

        assert len(investors) == 10
        assert total == 25
        assert has_more is True
        assert investors[0].name == "Investor 10"

    def test_get_last_page(self):
        """Test getting last page (partial)."""
        investors, total, has_more = self.service.get_paginated_investors(
            page=2, page_size=10)

        assert len(investors) == 5  # Only 5 remaining
        assert total == 25
        assert has_more is False
        assert investors[0].name == "Investor 20"

    def test_get_empty_page(self):
        """Test getting page beyond available data."""
        investors, total, has_more = self.service.get_paginated_investors(
            page=5, page_size=10)

        assert len(investors) == 0
        assert total == 25
        assert has_more is False

    def test_custom_page_size(self):
        """Test with custom page size."""
        investors, total, has_more = self.service.get_paginated_investors(
            page=0, page_size=5)

        assert len(investors) == 5
        assert total == 25
        assert has_more is True


class TestInvestorServiceInit:
    """Tests for InvestorService initialization."""

    def test_default_providers(self):
        """Test default provider names."""
        service = InvestorService()

        assert service.search_provider_name == "google"
        assert service.scraper_provider_name == "linkedin"

    def test_custom_providers(self):
        """Test custom provider names."""
        service = InvestorService(
            search_provider="custom_search",
            scraper_provider="custom_scraper"
        )

        assert service.search_provider_name == "custom_search"
        assert service.scraper_provider_name == "custom_scraper"
