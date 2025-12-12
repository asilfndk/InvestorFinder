"""
Conversation Memory Service for managing chat history and context.
Provides persistent conversation storage with search result integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import json
import asyncio
from pathlib import Path

from app.models import ChatMessage, MessageRole, InvestorProfile, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Holds the full context of a conversation."""

    conversation_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    investors: List[InvestorProfile] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    sectors_discussed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        ))
        self.updated_at = datetime.utcnow()

    def add_investors(self, investors: List[InvestorProfile]) -> None:
        """Add investors to the conversation context, avoiding duplicates."""
        existing_names = {inv.name.lower() for inv in self.investors}
        for inv in investors:
            if inv.name.lower() not in existing_names:
                self.investors.append(inv)
                existing_names.add(inv.name.lower())
        self.updated_at = datetime.utcnow()

    def add_search_results(self, results: List[SearchResult]) -> None:
        """Add search results to conversation, avoiding duplicates."""
        existing_urls = {r.url for r in self.search_results}
        for result in results:
            if result.url not in existing_urls:
                self.search_results.append(result)
                existing_urls.add(result.url)
        self.updated_at = datetime.utcnow()

    def add_sectors(self, sectors: List[str]) -> None:
        """Track discussed sectors."""
        for sector in sectors:
            if sector.lower() not in [s.lower() for s in self.sectors_discussed]:
                self.sectors_discussed.append(sector)
        self.updated_at = datetime.utcnow()

    def get_message_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get message history, optionally limited."""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation context."""
        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "investors_found": len(self.investors),
            "search_results_count": len(self.search_results),
            "sectors_discussed": self.sectors_discussed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ],
            "investors": [inv.model_dump(mode='json') for inv in self.investors],
            "search_results": [sr.model_dump(mode='json') for sr in self.search_results],
            "sectors_discussed": self.sectors_discussed,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Create from dictionary."""
        context = cls(
            conversation_id=data["conversation_id"],
            sectors_discussed=data.get("sectors_discussed", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

        # Restore messages
        for msg_data in data.get("messages", []):
            context.messages.append(ChatMessage(
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"])
            ))

        # Restore investors
        for inv_data in data.get("investors", []):
            context.investors.append(InvestorProfile(**inv_data))

        # Restore search results
        for sr_data in data.get("search_results", []):
            context.search_results.append(SearchResult(**sr_data))

        return context


class MemoryService:
    """
    Service for managing conversation memory.
    Supports in-memory storage with optional file persistence.
    """

    _instance: Optional["MemoryService"] = None

    def __new__(cls) -> "MemoryService":
        """Singleton pattern for global memory service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._conversations = {}
            cls._instance._max_conversations = 1000
            cls._instance._max_messages_per_conversation = 100
            cls._instance._ttl_hours = 24
            cls._instance._persistence_path = None
        return cls._instance

    def configure(
        self,
        max_conversations: int = 1000,
        max_messages: int = 100,
        ttl_hours: int = 24,
        persistence_path: Optional[str] = None
    ) -> None:
        """Configure memory service settings."""
        self._max_conversations = max_conversations
        self._max_messages_per_conversation = max_messages
        self._ttl_hours = ttl_hours
        if persistence_path:
            self._persistence_path = Path(persistence_path)
            self._persistence_path.mkdir(parents=True, exist_ok=True)

    def get_or_create_conversation(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation or create new one."""
        if conversation_id not in self._conversations:
            # Try to load from persistence
            if self._persistence_path:
                loaded = self._load_from_file(conversation_id)
                if loaded:
                    self._conversations[conversation_id] = loaded
                    return loaded

            # Create new conversation
            self._conversations[conversation_id] = ConversationContext(
                conversation_id=conversation_id
            )

            # Cleanup old conversations if needed
            self._cleanup_old_conversations()

        return self._conversations[conversation_id]

    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation by ID, returns None if not found."""
        if conversation_id in self._conversations:
            return self._conversations[conversation_id]

        # Try to load from persistence
        if self._persistence_path:
            loaded = self._load_from_file(conversation_id)
            if loaded:
                self._conversations[conversation_id] = loaded
                return loaded

        return None

    def save_conversation(self, context: ConversationContext) -> None:
        """Save conversation to memory and optionally to file."""
        # Trim messages if too many
        if len(context.messages) > self._max_messages_per_conversation:
            # Keep system context in first few messages
            context.messages = context.messages[-self._max_messages_per_conversation:]

        self._conversations[context.conversation_id] = context

        # Persist to file if configured
        if self._persistence_path:
            self._save_to_file(context)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]

            # Delete from persistence
            if self._persistence_path:
                file_path = self._persistence_path / f"{conversation_id}.json"
                if file_path.exists():
                    file_path.unlink()

            return True
        return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all active conversations."""
        return [
            context.get_summary()
            for context in self._conversations.values()
        ]

    def build_context_for_llm(
        self,
        conversation_id: str,
        new_message: str,
        new_investors: Optional[List[InvestorProfile]] = None,
        new_search_results: Optional[List[SearchResult]] = None,
        new_sectors: Optional[List[str]] = None,
        max_history: int = 20
    ) -> Dict[str, Any]:
        """
        Build complete context for LLM including memory and new data.
        This merges historical context with new search results.
        """
        context = self.get_or_create_conversation(conversation_id)

        # Add new data to context
        if new_investors:
            context.add_investors(new_investors)

        if new_search_results:
            context.add_search_results(new_search_results)

        if new_sectors:
            context.add_sectors(new_sectors)

        # Add user message
        context.add_message(MessageRole.USER, new_message)

        # Save updated context
        self.save_conversation(context)

        # Build LLM context
        return {
            "conversation_id": conversation_id,
            "messages": context.get_message_history(max_history),
            "investors": context.investors,
            "search_results": context.search_results[-20:],  # Last 20 results
            "sectors_discussed": context.sectors_discussed,
            "conversation_summary": context.get_summary()
        }

    def add_assistant_response(
        self,
        conversation_id: str,
        response: str
    ) -> None:
        """Add assistant response to conversation memory."""
        context = self.get_conversation(conversation_id)
        if context:
            context.add_message(MessageRole.ASSISTANT, response)
            self.save_conversation(context)

    def _cleanup_old_conversations(self) -> None:
        """Remove old conversations to prevent memory overflow."""
        if len(self._conversations) <= self._max_conversations:
            return

        cutoff_time = datetime.utcnow() - timedelta(hours=self._ttl_hours)

        # Find expired conversations
        expired = [
            cid for cid, ctx in self._conversations.items()
            if ctx.updated_at < cutoff_time
        ]

        # Remove expired
        for cid in expired:
            del self._conversations[cid]
            logger.debug(f"Cleaned up expired conversation: {cid}")

        # If still too many, remove oldest
        if len(self._conversations) > self._max_conversations:
            sorted_convs = sorted(
                self._conversations.items(),
                key=lambda x: x[1].updated_at
            )

            to_remove = len(self._conversations) - self._max_conversations
            for cid, _ in sorted_convs[:to_remove]:
                del self._conversations[cid]
                logger.debug(f"Cleaned up old conversation: {cid}")

    def _save_to_file(self, context: ConversationContext) -> None:
        """Save conversation to file."""
        if not self._persistence_path:
            return

        try:
            file_path = self._persistence_path / \
                f"{context.conversation_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(context.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save conversation to file: {e}")

    def _load_from_file(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load conversation from file."""
        if not self._persistence_path:
            return None

        try:
            file_path = self._persistence_path / f"{conversation_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return ConversationContext.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load conversation from file: {e}")

        return None

    def clear_all(self) -> None:
        """Clear all conversations (useful for testing)."""
        self._conversations.clear()
        logger.info("All conversations cleared")


# Global memory service instance
memory_service = MemoryService()


def get_memory_service() -> MemoryService:
    """Get the global memory service instance."""
    return memory_service
