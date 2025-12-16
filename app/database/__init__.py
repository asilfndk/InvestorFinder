"""
Database package for SQLAlchemy models and repository pattern.

This package provides:
- Async database connection management
- SQLAlchemy ORM models
- Repository pattern for clean data access
"""

from app.database.connection import (
    DatabaseManager,
    get_db,
    init_db,
    close_db,
    db_manager
)

from app.database.models import (
    Base,
    Conversation,
    Message,
    Investor,
    ConversationInvestor,
    SearchResultRecord,
    UserSession,
    ProviderUsage,
    User
)

from app.database.repositories import (
    ConversationRepository,
    MessageRepository,
    InvestorRepository,
    SearchResultRepository,
    UsageRepository
)

__all__ = [
    # Connection
    'DatabaseManager',
    'get_db',
    'init_db',
    'close_db',
    'db_manager',
    # Models
    'Base',
    'Conversation',
    'Message',
    'Investor',
    'ConversationInvestor',
    'SearchResultRecord',
    'UserSession',
    'ProviderUsage',
    # Repositories
    'ConversationRepository',
    'MessageRepository',
    'InvestorRepository',
    'SearchResultRepository',
    'UsageRepository',
]
