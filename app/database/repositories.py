"""
Repository pattern for database operations.
Provides clean interface for CRUD operations on all models.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, delete, update, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from app.database.models import (
    Conversation, Message, Investor,
    ConversationInvestor, SearchResultRecord,
    ProviderUsage
)
from app.models import (
    ChatMessage, MessageRole,
    InvestorProfile, SearchResult
)

logger = logging.getLogger(__name__)


class ConversationRepository:
    """
    Repository for Conversation CRUD operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation_id: str) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(id=conversation_id)
        self.session.add(conversation)
        await self.session.flush()
        logger.debug(f"Created conversation: {conversation_id}")
        return conversation

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID with related data."""
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.investors).selectinload(
                    ConversationInvestor.investor),
                selectinload(Conversation.search_results)
            )
            .where(Conversation.id == conversation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, conversation_id: str) -> Conversation:
        """Get existing or create new conversation."""
        conversation = await self.get(conversation_id)
        if not conversation:
            conversation = await self.create(conversation_id)
        return conversation

    async def update_sectors(
        self,
        conversation_id: str,
        sectors: List[str]
    ) -> None:
        """Update sectors discussed in conversation."""
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                sectors_discussed=sectors,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.execute(stmt)

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and all related data."""
        stmt = delete(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def list_active(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """List active conversations."""
        stmt = (
            select(Conversation)
            .where(Conversation.is_active == True)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old(self, hours: int = 24) -> int:
        """Delete conversations older than specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            delete(Conversation)
            .where(Conversation.updated_at < cutoff)
        )
        result = await self.session.execute(stmt)
        logger.info(f"Cleaned up {result.rowcount} old conversations")
        return result.rowcount


class MessageRepository:
    """
    Repository for Message CRUD operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        conversation_id: str,
        role: str,
        content: str,
        token_count: Optional[int] = None
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get message history for a conversation."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, conversation_id: str) -> int:
        """Count messages in a conversation."""
        stmt = (
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class InvestorRepository:
    """
    Repository for Investor CRUD operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_linkedin(self, linkedin_url: str) -> Optional[Investor]:
        """Get investor by LinkedIn URL."""
        stmt = select(Investor).where(Investor.linkedin_url == linkedin_url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Investor]:
        """Get investor by name (case-insensitive)."""
        stmt = select(Investor).where(Investor.name_lower == name.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, profile: InvestorProfile) -> Investor:
        """Create a new investor from profile."""
        investor = Investor(
            name=profile.name,
            name_lower=profile.name.lower(),
            title=profile.title,
            company=profile.company,
            email=profile.email,
            linkedin_url=profile.linkedin_url,
            location=getattr(profile, 'location', None),
            bio=getattr(profile, 'bio', None),
            investment_focus=getattr(profile, 'investment_focus', []),
            source=getattr(profile, 'source', None),
            enriched='enriched' in (getattr(profile, 'source', '') or '')
        )
        self.session.add(investor)
        await self.session.flush()
        return investor

    async def get_or_create(self, profile: InvestorProfile) -> Investor:
        """Get existing investor or create new one."""
        # Try LinkedIn URL first (more unique)
        if profile.linkedin_url:
            investor = await self.get_by_linkedin(profile.linkedin_url)
            if investor:
                return investor

        # Try name
        investor = await self.get_by_name(profile.name)
        if investor:
            return investor

        # Create new
        return await self.create(profile)

    async def update(self, investor_id: int, **kwargs) -> None:
        """Update investor fields."""
        kwargs['updated_at'] = datetime.utcnow()
        stmt = (
            update(Investor)
            .where(Investor.id == investor_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)

    async def search(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50
    ) -> List[Investor]:
        """Search investors with filters."""
        stmt = select(Investor)

        if query:
            stmt = stmt.where(
                Investor.name_lower.contains(query.lower())
            )
        if company:
            stmt = stmt.where(Investor.company.contains(company))
        if source:
            stmt = stmt.where(Investor.source == source)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_to_conversation(
        self,
        conversation_id: str,
        investor_id: int,
        page_number: int = 0
    ) -> ConversationInvestor:
        """Link investor to a conversation."""
        link = ConversationInvestor(
            conversation_id=conversation_id,
            investor_id=investor_id,
            page_number=page_number
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_for_conversation(
        self,
        conversation_id: str,
        page: Optional[int] = None,
        limit: int = 10
    ) -> List[Investor]:
        """Get investors for a conversation, optionally by page."""
        stmt = (
            select(Investor)
            .join(ConversationInvestor)
            .where(ConversationInvestor.conversation_id == conversation_id)
        )

        if page is not None:
            stmt = stmt.where(ConversationInvestor.page_number == page)

        stmt = stmt.order_by(ConversationInvestor.added_at).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class SearchResultRepository:
    """
    Repository for SearchResult CRUD operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_many(
        self,
        conversation_id: str,
        results: List[SearchResult]
    ) -> List[SearchResultRecord]:
        """Add multiple search results to a conversation."""
        records = []
        for r in results:
            record = SearchResultRecord(
                conversation_id=conversation_id,
                title=r.title,
                url=r.url,
                snippet=r.snippet
            )
            self.session.add(record)
            records.append(record)

        await self.session.flush()
        return records

    async def get_for_conversation(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[SearchResultRecord]:
        """Get search results for a conversation."""
        stmt = (
            select(SearchResultRecord)
            .where(SearchResultRecord.conversation_id == conversation_id)
            .order_by(SearchResultRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class UsageRepository:
    """
    Repository for tracking provider usage.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        provider_type: str,
        provider_name: str,
        conversation_id: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> ProviderUsage:
        """Record a provider usage event."""
        usage = ProviderUsage(
            provider_type=provider_type,
            provider_name=provider_name,
            conversation_id=conversation_id,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message
        )
        self.session.add(usage)
        await self.session.flush()
        return usage

    async def get_stats(
        self,
        provider_type: Optional[str] = None,
        provider_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage statistics."""
        stmt = select(
            func.count(ProviderUsage.id).label('total_requests'),
            func.sum(ProviderUsage.tokens_used).label('total_tokens'),
            func.avg(ProviderUsage.response_time_ms).label(
                'avg_response_time'),
            func.sum(
                func.cast(ProviderUsage.success == False, Integer)
            ).label('error_count')
        )

        if provider_type:
            stmt = stmt.where(ProviderUsage.provider_type == provider_type)
        if provider_name:
            stmt = stmt.where(ProviderUsage.provider_name == provider_name)
        if since:
            stmt = stmt.where(ProviderUsage.timestamp >= since)

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            'total_requests': row.total_requests or 0,
            'total_tokens': row.total_tokens or 0,
            'avg_response_time_ms': float(row.avg_response_time or 0),
            'error_count': row.error_count or 0
        }
