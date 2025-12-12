"""
Database models for conversation and investor storage.
Uses SQLAlchemy ORM with async support.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Integer, Float,
    ForeignKey, JSON, Boolean, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Conversation(Base):
    """
    Represents a chat conversation.
    Stores metadata and links to messages and investors.
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    sectors_discussed: Mapped[dict] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    investors: Mapped[List["ConversationInvestor"]] = relationship(
        "ConversationInvestor", back_populates="conversation", cascade="all, delete-orphan"
    )
    search_results: Mapped[List["SearchResultRecord"]] = relationship(
        "SearchResultRecord", back_populates="conversation", cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_conversation_updated", "updated_at"),
        Index("idx_conversation_active", "is_active"),
    )


class Message(Base):
    """
    Represents a chat message within a conversation.
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    # Token tracking for analytics
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_message_conversation", "conversation_id"),
        Index("idx_message_timestamp", "timestamp"),
    )


class Investor(Base):
    """
    Represents an investor profile.
    Shared across conversations to avoid duplicates.
    """
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_lower: Mapped[str] = mapped_column(
        String(255), index=True)  # For case-insensitive lookup
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, unique=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    investment_focus: Mapped[dict] = mapped_column(JSON, default=list)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    enriched: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    conversations: Mapped[List["ConversationInvestor"]] = relationship(
        "ConversationInvestor", back_populates="investor"
    )

    __table_args__ = (
        Index("idx_investor_name", "name_lower"),
        Index("idx_investor_company", "company"),
        Index("idx_investor_source", "source"),
    )


class ConversationInvestor(Base):
    """
    Many-to-many relationship between conversations and investors.
    Tracks when an investor was found in a specific conversation.
    """
    __tablename__ = "conversation_investors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    investor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investors.id", ondelete="CASCADE")
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    page_number: Mapped[int] = mapped_column(
        Integer, default=0)  # For pagination tracking

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="investors"
    )
    investor: Mapped["Investor"] = relationship(
        "Investor", back_populates="conversations"
    )

    __table_args__ = (
        Index("idx_conv_investor", "conversation_id",
              "investor_id", unique=True),
    )


class SearchResultRecord(Base):
    """
    Stores search results for reference and caching.
    """
    __tablename__ = "search_results"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    # Relationship
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="search_results"
    )

    __table_args__ = (
        Index("idx_search_conversation", "conversation_id"),
        Index("idx_search_url", "url"),
    )


class UserSession(Base):
    """
    Tracks user sessions for analytics and rate limiting.
    """
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    request_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_session_activity", "last_activity"),
    )


class ProviderUsage(Base):
    """
    Tracks API provider usage for monitoring and billing.
    """
    __tablename__ = "provider_usage"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    provider_type: Mapped[str] = mapped_column(
        String(50))  # 'llm', 'search', 'scraper'
    # 'gemini', 'google', etc.
    provider_name: Mapped[str] = mapped_column(String(50))
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True)

    # Usage metrics
    request_count: Mapped[int] = mapped_column(Integer, default=1)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[int]
                             ] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_usage_provider", "provider_type", "provider_name"),
        Index("idx_usage_timestamp", "timestamp"),
    )
