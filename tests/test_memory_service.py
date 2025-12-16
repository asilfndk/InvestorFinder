"""
Unit tests for MemoryService and ConversationContext.
"""

from app.models import InvestorProfile, SearchResult, MessageRole
from app.services.memory_service import MemoryService, ConversationContext
import sys
from pathlib import Path
import pytest
from datetime import datetime

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestConversationContext:
    """Tests for ConversationContext dataclass."""

    def test_create_context(self):
        """Test creating a new conversation context."""
        context = ConversationContext(conversation_id="test-123")

        assert context.conversation_id == "test-123"
        assert len(context.messages) == 0
        assert len(context.investors) == 0
        assert len(context.search_results) == 0
        assert len(context.sectors_discussed) == 0

    def test_add_message(self):
        """Test adding messages to context."""
        context = ConversationContext(conversation_id="test-123")

        context.add_message(MessageRole.USER, "Hello")
        context.add_message(MessageRole.ASSISTANT, "Hi there!")

        assert len(context.messages) == 2
        assert context.messages[0].role == MessageRole.USER
        assert context.messages[0].content == "Hello"
        assert context.messages[1].role == MessageRole.ASSISTANT

    def test_add_investors_deduplication(self):
        """Test that duplicate investors are not added."""
        context = ConversationContext(conversation_id="test-123")

        inv1 = InvestorProfile(name="John Doe", source="test")
        inv2 = InvestorProfile(name="Jane Smith", source="test")
        # Duplicate (case insensitive)
        inv3 = InvestorProfile(name="john doe", source="test")

        context.add_investors([inv1, inv2, inv3])

        assert len(context.investors) == 2  # inv3 should be deduplicated

    def test_add_search_results_deduplication(self):
        """Test that duplicate search results are not added."""
        context = ConversationContext(conversation_id="test-123")

        sr1 = SearchResult(
            title="Result 1", url="https://example.com/1", snippet="Test")
        sr2 = SearchResult(
            title="Result 2", url="https://example.com/2", snippet="Test")
        sr3 = SearchResult(
            title="Result 3", url="https://example.com/1", snippet="Duplicate URL")

        context.add_search_results([sr1, sr2, sr3])

        assert len(context.search_results) == 2  # sr3 should be deduplicated

    def test_add_sectors(self):
        """Test adding sectors to context."""
        context = ConversationContext(conversation_id="test-123")

        context.add_sectors(["ai", "healthcare"])
        # AI is duplicate (case insensitive)
        context.add_sectors(["AI", "fintech"])

        assert len(context.sectors_discussed) == 3
        assert "ai" in context.sectors_discussed
        assert "healthcare" in context.sectors_discussed
        assert "fintech" in context.sectors_discussed

    def test_get_message_history_with_limit(self):
        """Test getting limited message history."""
        context = ConversationContext(conversation_id="test-123")

        for i in range(10):
            context.add_message(MessageRole.USER, f"Message {i}")

        history = context.get_message_history(limit=5)

        assert len(history) == 5
        assert history[0].content == "Message 5"  # Last 5 messages
        assert history[4].content == "Message 9"

    def test_get_summary(self):
        """Test getting conversation summary."""
        context = ConversationContext(conversation_id="test-123")
        context.add_message(MessageRole.USER, "Hello")
        context.add_investors(
            [InvestorProfile(name="John Doe", source="test")])
        context.add_sectors(["ai"])

        summary = context.get_summary()

        assert summary["conversation_id"] == "test-123"
        assert summary["message_count"] == 1
        assert summary["investors_found"] == 1
        assert "ai" in summary["sectors_discussed"]

    def test_serialization(self):
        """Test to_dict and from_dict serialization."""
        context = ConversationContext(conversation_id="test-123")
        context.add_message(MessageRole.USER, "Hello")
        context.add_investors(
            [InvestorProfile(name="John Doe", source="test")])
        context.add_sectors(["ai"])

        data = context.to_dict()
        restored = ConversationContext.from_dict(data)

        assert restored.conversation_id == context.conversation_id
        assert len(restored.messages) == len(context.messages)
        assert len(restored.investors) == len(context.investors)
        assert restored.sectors_discussed == context.sectors_discussed


class TestMemoryService:
    """Tests for MemoryService."""

    def setup_method(self):
        """Reset memory service singleton before each test."""
        # Create a fresh instance by clearing the singleton
        MemoryService._instance = None
        self.service = MemoryService()

    def teardown_method(self):
        """Clear memory service after each test."""
        if hasattr(self, 'service'):
            self.service.clear_all()
        MemoryService._instance = None

    def test_singleton_pattern(self):
        """Test that MemoryService is a singleton."""
        service1 = MemoryService()
        service2 = MemoryService()

        assert service1 is service2

    def test_get_or_create_conversation(self):
        """Test creating new conversation."""
        context = self.service.get_or_create_conversation("new-conv-id")

        assert context is not None
        assert context.conversation_id == "new-conv-id"

    def test_get_existing_conversation(self):
        """Test getting existing conversation."""
        context1 = self.service.get_or_create_conversation("existing-id")
        context1.add_message(MessageRole.USER, "Test message")

        context2 = self.service.get_or_create_conversation("existing-id")

        assert len(context2.messages) == 1
        assert context2.messages[0].content == "Test message"

    def test_get_conversation_not_found(self):
        """Test getting non-existent conversation."""
        context = self.service.get_conversation("non-existent-id")

        assert context is None

    def test_delete_conversation(self):
        """Test deleting conversation."""
        self.service.get_or_create_conversation("to-delete")

        result = self.service.delete_conversation("to-delete")

        assert result is True
        assert self.service.get_conversation("to-delete") is None

    def test_delete_nonexistent_conversation(self):
        """Test deleting non-existent conversation."""
        result = self.service.delete_conversation("non-existent")

        assert result is False

    def test_list_conversations(self):
        """Test listing all conversations."""
        self.service.get_or_create_conversation("conv-1")
        self.service.get_or_create_conversation("conv-2")
        self.service.get_or_create_conversation("conv-3")

        conversations = self.service.list_conversations()

        assert len(conversations) == 3

    def test_build_context_for_llm(self):
        """Test building LLM context."""
        context = self.service.build_context_for_llm(
            conversation_id="llm-test",
            new_message="Find AI investors",
            new_investors=[InvestorProfile(name="John Doe", source="test")],
            new_sectors=["ai"]
        )

        assert context["conversation_id"] == "llm-test"
        assert len(context["messages"]) == 1
        assert len(context["investors"]) == 1
        assert "ai" in context["sectors_discussed"]

    def test_add_assistant_response(self):
        """Test adding assistant response."""
        self.service.get_or_create_conversation("response-test")
        self.service.build_context_for_llm("response-test", "User message")

        self.service.add_assistant_response(
            "response-test", "Assistant response")

        context = self.service.get_conversation("response-test")
        assert len(context.messages) == 2
        assert context.messages[1].role == MessageRole.ASSISTANT
        assert context.messages[1].content == "Assistant response"

    def test_clear_all(self):
        """Test clearing all conversations."""
        self.service.get_or_create_conversation("conv-1")
        self.service.get_or_create_conversation("conv-2")

        self.service.clear_all()

        assert len(self.service.list_conversations()) == 0
