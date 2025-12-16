"""
Integration tests for API routes.
"""

from app.main import app
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import pytest

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_api_health_check(self):
        """Test /api/health endpoint."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data
        assert "timestamp" in data


class TestInfoEndpoint:
    """Tests for application info endpoint."""

    def test_info_endpoint(self):
        """Test /info endpoint."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "available_providers" in data
        assert "llm" in data["available_providers"]


class TestProvidersEndpoint:
    """Tests for providers listing endpoint."""

    def test_list_providers(self):
        """Test /api/providers endpoint."""
        response = client.get("/api/providers")

        assert response.status_code == 200
        data = response.json()

        assert "llm_providers" in data
        assert "search_providers" in data
        assert "scraper_providers" in data

        # Check that gemini is in llm providers
        assert "gemini" in data["llm_providers"]


class TestChatEndpoint:
    """Tests for chat endpoints."""

    def test_chat_validation_empty_message(self):
        """Test that empty message returns error."""
        response = client.post(
            "/api/chat",
            json={"message": ""}
        )

        assert response.status_code == 422  # Validation error

    def test_chat_validation_whitespace_message(self):
        """Test that whitespace-only message returns error."""
        response = client.post(
            "/api/chat",
            json={"message": "   "}
        )

        assert response.status_code == 422  # Validation error

    def test_chat_validation_too_long_message(self):
        """Test that too long message returns error."""
        long_message = "x" * 5001  # Max is 5000
        response = client.post(
            "/api/chat",
            json={"message": long_message}
        )

        assert response.status_code == 422  # Validation error


class TestConversationEndpoints:
    """Tests for conversation management endpoints."""

    def test_list_conversations(self):
        """Test /api/conversations endpoint."""
        response = client.get("/api/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert isinstance(data["conversations"], list)

    def test_get_nonexistent_conversation(self):
        """Test getting non-existent conversation returns 404."""
        response = client.get("/api/conversation/non-existent-id")

        assert response.status_code == 404

    def test_delete_nonexistent_conversation(self):
        """Test deleting non-existent conversation returns 404."""
        response = client.delete("/api/conversation/non-existent-id")

        assert response.status_code == 404


class TestInvestorSearchEndpoint:
    """Tests for investor search endpoint."""

    def test_search_validation_empty_sectors(self):
        """Test that empty sectors returns error."""
        response = client.post(
            "/api/search-investors",
            json={"sectors": []}
        )

        assert response.status_code == 422  # Validation error

    def test_search_validation_invalid_limit(self):
        """Test that invalid limit returns error."""
        response = client.post(
            "/api/search-investors",
            json={"sectors": ["ai"], "limit": 0}
        )

        assert response.status_code == 422  # Validation error

    def test_search_validation_limit_too_high(self):
        """Test that limit > 50 returns error."""
        response = client.post(
            "/api/search-investors",
            json={"sectors": ["ai"], "limit": 100}
        )

        assert response.status_code == 422  # Validation error


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_html(self):
        """Test / returns HTML page."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
