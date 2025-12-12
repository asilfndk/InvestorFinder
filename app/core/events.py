"""
Event system for decoupled communication between components.
Implements a simple pub/sub pattern for application events.
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Enumeration of event types in the application."""

    # Chat events
    CHAT_MESSAGE_RECEIVED = "chat.message.received"
    CHAT_RESPONSE_GENERATED = "chat.response.generated"

    # Search events
    SEARCH_STARTED = "search.started"
    SEARCH_COMPLETED = "search.completed"
    SEARCH_FAILED = "search.failed"

    # Scraping events
    SCRAPE_STARTED = "scrape.started"
    SCRAPE_COMPLETED = "scrape.completed"
    SCRAPE_FAILED = "scrape.failed"

    # Investor events
    INVESTOR_FOUND = "investor.found"
    INVESTOR_SAVED = "investor.saved"

    # System events
    PROVIDER_INITIALIZED = "provider.initialized"
    PROVIDER_ERROR = "provider.error"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


@dataclass
class Event:
    """Represents an application event."""

    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Any]


class EventBus:
    """
    Simple event bus for pub/sub communication.
    Allows components to communicate without tight coupling.
    """

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._async_handlers = {}
        return cls._instance

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if asyncio.iscoroutinefunction(handler):
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

        logger.debug(f"Handler subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if event_type in self._async_handlers and handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        logger.debug(f"Publishing event: {event.type.value}")

        # Call sync handlers
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in sync event handler: {e}")

        # Call async handlers
        if event.type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event.type]:
                tasks.append(self._safe_call_async(handler, event))

            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_call_async(self, handler: EventHandler, event: Event) -> None:
        """Safely call an async handler, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in async event handler: {e}")

    def clear(self) -> None:
        """Clear all handlers (useful for testing)."""
        self._handlers.clear()
        self._async_handlers.clear()


# Global event bus instance
event_bus = EventBus()
