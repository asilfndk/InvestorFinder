"""
Database-backed Memory Service for managing chat history and context.
Provides persistent conversation storage using SQLAlchemy async.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, MessageRole, InvestorProfile, SearchResult
from app.database.repositories import (
    ConversationRepository,
    MessageRepository,
    InvestorRepository,
    SearchResultRepository,
    UsageRepository
)
from app.database.models import (
    Conversation as DBConversation,
    Message as DBMessage,
    Investor as DBInvestor
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Holds the full context of a conversation in memory."""

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


class DatabaseMemoryService:
    """
    Service for managing conversation memory with database persistence.
    Uses SQLAlchemy async for all database operations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.investor_repo = InvestorRepository(session)
        self.search_result_repo = SearchResultRepository(session)
        self.usage_repo = UsageRepository(session)

        # In-memory cache for current session
        self._context_cache: Dict[str, ConversationContext] = {}
        self._max_messages_per_conversation = 100

    async def get_or_create_conversation(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation or create new one."""
        # Check cache first
        if conversation_id in self._context_cache:
            return self._context_cache[conversation_id]

        # Try to load from database
        db_conversation = await self.conversation_repo.get(conversation_id)

        if db_conversation:
            context = await self._db_to_context(db_conversation)
        else:
            # Create new conversation in database
            await self.conversation_repo.create(conversation_id)
            await self.session.commit()
            context = ConversationContext(conversation_id=conversation_id)

        self._context_cache[conversation_id] = context
        return context

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation by ID, returns None if not found."""
        # Check cache first
        if conversation_id in self._context_cache:
            return self._context_cache[conversation_id]

        # Try to load from database
        db_conversation = await self.conversation_repo.get(conversation_id)

        if db_conversation:
            context = await self._db_to_context(db_conversation)
            self._context_cache[conversation_id] = context
            return context

        return None

    async def save_conversation(self, context: ConversationContext) -> None:
        """Save conversation to database."""
        try:
            # Update sectors in database
            await self.conversation_repo.update_sectors(
                context.conversation_id,
                context.sectors_discussed
            )
            await self.session.commit()

            # Update cache
            self._context_cache[context.conversation_id] = context
            logger.debug(f"Saved conversation: {context.conversation_id}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save conversation: {e}")
            raise

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        token_count: Optional[int] = None
    ) -> None:
        """Add a message to the conversation in database."""
        try:
            await self.message_repo.add(
                conversation_id=conversation_id,
                role=role.value,
                content=content,
                token_count=token_count
            )
            await self.session.commit()

            # Update cache if present
            if conversation_id in self._context_cache:
                self._context_cache[conversation_id].add_message(role, content)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to add message: {e}")
            raise

    async def add_investors(
        self,
        conversation_id: str,
        investors: List[InvestorProfile],
        page_number: int = 0
    ) -> None:
        """Add investors to conversation in database."""
        try:
            for inv_profile in investors:
                # Get or create investor in shared table
                investor = await self.investor_repo.get_or_create(inv_profile)

                # Link to conversation
                await self.investor_repo.add_to_conversation(
                    conversation_id=conversation_id,
                    investor_id=investor.id,
                    page_number=page_number
                )

            await self.session.commit()

            # Update cache
            if conversation_id in self._context_cache:
                self._context_cache[conversation_id].add_investors(investors)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to add investors: {e}")
            raise

    async def add_search_results(
        self,
        conversation_id: str,
        results: List[SearchResult]
    ) -> None:
        """Add search results to conversation in database."""
        try:
            await self.search_result_repo.add_many(conversation_id, results)
            await self.session.commit()

            # Update cache
            if conversation_id in self._context_cache:
                self._context_cache[conversation_id].add_search_results(
                    results)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to add search results: {e}")
            raise

    async def add_sectors(
        self,
        conversation_id: str,
        sectors: List[str]
    ) -> None:
        """Add sectors to conversation in database."""
        context = await self.get_or_create_conversation(conversation_id)
        context.add_sectors(sectors)
        await self.save_conversation(context)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all related data."""
        try:
            success = await self.conversation_repo.delete(conversation_id)
            await self.session.commit()

            # Remove from cache
            if conversation_id in self._context_cache:
                del self._context_cache[conversation_id]

            return success

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete conversation: {e}")
            return False

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all active conversations."""
        conversations = await self.conversation_repo.list_active(limit, offset)
        return [
            {
                "conversation_id": c.id,
                "sectors_discussed": c.sectors_discussed or [],
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in conversations
        ]

    async def build_context_for_llm(
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
        """
        context = await self.get_or_create_conversation(conversation_id)

        # Add new data
        if new_investors:
            await self.add_investors(conversation_id, new_investors)

        if new_search_results:
            await self.add_search_results(conversation_id, new_search_results)

        if new_sectors:
            await self.add_sectors(conversation_id, new_sectors)

        # Add user message
        await self.add_message(conversation_id, MessageRole.USER, new_message)

        # Refresh context from cache
        context = self._context_cache.get(conversation_id, context)

        # Build LLM context
        return {
            "conversation_id": conversation_id,
            "messages": context.get_message_history(max_history),
            "investors": context.investors,
            "search_results": context.search_results[-20:],
            "sectors_discussed": context.sectors_discussed,
            "conversation_summary": context.get_summary()
        }

    async def add_assistant_response(
        self,
        conversation_id: str,
        response: str
    ) -> None:
        """Add assistant response to conversation memory."""
        await self.add_message(conversation_id, MessageRole.ASSISTANT, response)

    async def record_provider_usage(
        self,
        provider_type: str,
        provider_name: str,
        conversation_id: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Record provider usage for analytics."""
        try:
            await self.usage_repo.record(
                provider_type=provider_type,
                provider_name=provider_name,
                conversation_id=conversation_id,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
                success=success,
                error_message=error_message
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to record usage: {e}")

    async def cleanup_old_conversations(self, hours: int = 24) -> int:
        """Remove old conversations from database."""
        count = await self.conversation_repo.cleanup_old(hours)
        await self.session.commit()
        return count

    async def _db_to_context(self, db_conv: DBConversation) -> ConversationContext:
        """Convert database model to ConversationContext."""
        context = ConversationContext(
            conversation_id=db_conv.id,
            sectors_discussed=db_conv.sectors_discussed or [],
            metadata=db_conv.extra_data or {},
            created_at=db_conv.created_at,
            updated_at=db_conv.updated_at
        )

        # Convert messages
        for msg in db_conv.messages:
            context.messages.append(ChatMessage(
                role=MessageRole(msg.role),
                content=msg.content,
                timestamp=msg.timestamp
            ))

        # Convert investors
        for conv_inv in db_conv.investors:
            inv = conv_inv.investor
            context.investors.append(InvestorProfile(
                name=inv.name,
                title=inv.title,
                company=inv.company,
                email=inv.email,
                linkedin_url=inv.linkedin_url,
                source=inv.source
            ))

        # Convert search results
        for sr in db_conv.search_results:
            context.search_results.append(SearchResult(
                title=sr.title,
                url=sr.url,
                snippet=sr.snippet
            ))

        return context


# Dependency injection helper
async def get_db_memory_service(session: AsyncSession) -> DatabaseMemoryService:
    """Get database memory service for a session."""
    return DatabaseMemoryService(session)
