"""
Chat Service - Orchestrates chat interactions with LLM, search, and scraping.
Includes conversation memory for context persistence.
"""

from typing import List, Optional, Dict, Any, AsyncIterator
import uuid
import time
import logging
import asyncio

from app.core.protocols import LLMConfig
from app.core.providers import get_llm, registry
from app.core.exceptions import AppException
from app.core.events import event_bus, Event, EventType
from app.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    InvestorProfile,
    SearchResult,
    MessageRole,
)
from app.services.investor_service import InvestorService
from app.services.memory_service import MemoryService, get_memory_service

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for handling chat interactions with persistent memory.
    Orchestrates LLM, search, scraping providers, and conversation memory.
    """

    # Sector keywords for extraction (English only for US focus)
    SECTOR_KEYWORDS = {
        "healthcare": ["health", "healthcare", "medical", "biotech", "medtech", "pharma", "healthtech"],
        "ecommerce": ["ecommerce", "e-commerce", "retail", "marketplace", "dtc", "direct to consumer"],
        "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "generative ai"],
        "fintech": ["fintech", "finance", "payment", "banking", "neobank", "defi", "crypto", "blockchain"],
        "edtech": ["edtech", "education", "learning", "online education", "e-learning"],
        "saas": ["saas", "software", "b2b", "enterprise", "cloud", "platform"],
        "climate": ["climate", "cleantech", "sustainability", "green", "renewable", "carbon"],
        "gaming": ["gaming", "game", "entertainment", "esports", "metaverse"],
        "foodtech": ["food", "foodtech", "agtech", "agriculture", "delivery"],
        "logistics": ["logistics", "supply chain", "shipping", "freight", "warehouse"],
        "proptech": ["proptech", "real estate", "property", "housing"],
        "cybersecurity": ["cybersecurity", "security", "infosec", "privacy"],
        "robotics": ["robotics", "automation", "manufacturing", "hardware"],
    }

    # Triggers for investor search (English)
    SEARCH_TRIGGERS = [
        "investor", "investors", "investment", "invest",
        "funding", "capital", "raise", "raising",
        "find", "search", "look for", "looking for",
        "startup", "venture", "vc", "angel",
        "seed", "series a", "series b"
    ]

    # Triggers for showing more investors (pagination)
    MORE_INVESTORS_TRIGGERS = [
        "more", "next", "continue", "show more",
        "additional", "other investors", "remaining",
        "next 10", "more investors"
    ]

    def __init__(
        self,
        default_llm_provider: str = "gemini",
        default_model: str = "gemini-2.0-flash"
    ):
        self.default_llm_provider = default_llm_provider
        self.default_model = default_model
        self._llm_provider = None
        self._investor_service = InvestorService()
        self._memory_service: MemoryService = get_memory_service()
        # Pagination state per conversation
        self._pagination_state: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize the chat service with default provider."""
        config = LLMConfig(model_name=self.default_model)
        self._llm_provider = await get_llm(
            self.default_llm_provider,
            config
        )

        # Configure memory service
        self._memory_service.configure(
            max_conversations=1000,
            max_messages=100,
            ttl_hours=24,
            persistence_path="data/conversations"
        )

        logger.info("Chat service initialized with memory support")

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process a chat message with memory context and return response."""
        start_time = time.time()

        # Generate conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Publish event
        await event_bus.publish(Event(
            type=EventType.CHAT_MESSAGE_RECEIVED,
            data={"message": request.message,
                  "conversation_id": conversation_id}
        ))

        # Determine which LLM provider to use
        provider_name = request.model_provider or self.default_llm_provider

        # Get or create LLM provider
        try:
            if provider_name != self.default_llm_provider or not self._llm_provider:
                config = LLMConfig(
                    model_name=self._get_default_model(provider_name))
                llm_provider = await get_llm(provider_name, config)
            else:
                llm_provider = self._llm_provider
        except Exception as e:
            logger.error(f"Failed to get LLM provider: {e}")
            return ChatResponse(
                message=f"Sorry, failed to initialize the model provider: {str(e)}",
                conversation_id=conversation_id
            )

        # Check if we need to search for investors
        new_search_results: List[SearchResult] = []
        new_investors: List[InvestorProfile] = []
        sectors: List[str] = []

        if self._should_search_investors(request.message):
            sectors = self._extract_sectors(request.message)

            try:
                # Request more investors for comprehensive results
                new_investors, new_search_results = await self._investor_service.find_investors(
                    sectors=sectors,
                    num_results=30  # Get more results
                )
                logger.info(
                    f"Found {len(new_investors)} new investors for sectors: {sectors}")
            except Exception as e:
                logger.error(f"Investor search failed: {e}")

        # Build context with memory - this merges history with new data
        llm_context = self._memory_service.build_context_for_llm(
            conversation_id=conversation_id,
            new_message=request.message,
            new_investors=new_investors,
            new_search_results=new_search_results,
            new_sectors=sectors,
            max_history=20
        )

        # Get conversation context for returning all accumulated investors
        conversation = self._memory_service.get_conversation(conversation_id)
        all_investors = conversation.investors if conversation else new_investors
        all_search_results = conversation.search_results if conversation else new_search_results

        # Generate response with full context
        try:
            response_text = await llm_provider.generate_response(
                messages=llm_context["messages"],
                context={
                    "conversation_id": conversation_id,
                    "investors": all_investors,
                    "search_results": llm_context["search_results"],
                    "sectors_discussed": llm_context["sectors_discussed"],
                    "conversation_summary": llm_context["conversation_summary"]
                }
            )

            # Save assistant response to memory
            self._memory_service.add_assistant_response(
                conversation_id, response_text)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            response_text = f"Sorry, an error occurred while generating a response: {str(e)}"

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Publish event
        await event_bus.publish(Event(
            type=EventType.CHAT_RESPONSE_GENERATED,
            data={
                "conversation_id": conversation_id,
                "processing_time_ms": processing_time,
                "investors_in_memory": len(all_investors)
            }
        ))

        # Get sectors from memory context
        sectors_discussed = llm_context.get("sectors_discussed", [])

        return ChatResponse(
            message=response_text,
            investors=all_investors,  # Return all accumulated investors
            search_results=all_search_results[-10:],  # Last 10 search results
            conversation_id=conversation_id,
            sectors_discussed=sectors_discussed,
            total_investors_found=len(all_investors),
            model_used=provider_name,
            processing_time_ms=processing_time
        )

    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a conversation including all found investors."""
        context = self._memory_service.get_conversation(conversation_id)
        if context:
            return context.get_summary()
        return None

    async def process_message_stream(
        self,
        request: ChatRequest
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a chat message and stream the response.
        Yields chunks of data including text, investors, and metadata.
        Supports pagination with 10 investors per request.
        """
        start_time = time.time()

        # Generate conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Initialize pagination state for this conversation if needed
        if conversation_id not in self._pagination_state:
            self._pagination_state[conversation_id] = {
                "current_page": 0,
                "all_investors": [],
                "page_size": 10
            }

        # Yield initial metadata
        yield {
            "type": "start",
            "conversation_id": conversation_id
        }

        # Publish event
        await event_bus.publish(Event(
            type=EventType.CHAT_MESSAGE_RECEIVED,
            data={"message": request.message,
                  "conversation_id": conversation_id}
        ))

        # Check if user wants more investors (pagination)
        is_pagination_request = self._is_pagination_request(request.message)

        # Get LLM provider
        provider_name = request.model_provider or self.default_llm_provider
        try:
            if provider_name != self.default_llm_provider or not self._llm_provider:
                config = LLMConfig(
                    model_name=self._get_default_model(provider_name))
                llm_provider = await get_llm(provider_name, config)
            else:
                llm_provider = self._llm_provider
        except Exception as e:
            logger.error(f"Failed to get LLM provider: {e}")
            yield {
                "type": "error",
                "error": f"Model sağlayıcısı başlatılamadı: {str(e)}"
            }
            return

        # Handle pagination or new search
        new_search_results: List[SearchResult] = []
        new_investors: List[InvestorProfile] = []
        sectors: List[str] = []
        current_page_investors: List[InvestorProfile] = []

        if is_pagination_request:
            # Get next page of investors
            state = self._pagination_state[conversation_id]
            all_investors = state["all_investors"]
            page_size = state["page_size"]
            current_page = state["current_page"] + 1

            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(all_investors))

            if start_idx < len(all_investors):
                current_page_investors = all_investors[start_idx:end_idx]
                state["current_page"] = current_page

                yield {
                    "type": "status",
                    "message": f"📝 Sonraki {len(current_page_investors)} yatırımcı gösteriliyor... ({start_idx + 1}-{end_idx}/{len(all_investors)})"
                }

                remaining = len(all_investors) - end_idx
                yield {
                    "type": "pagination_info",
                    "current_page": current_page,
                    "showing": len(current_page_investors),
                    "total": len(all_investors),
                    "has_more": remaining > 0,
                    "remaining": remaining
                }
            else:
                yield {
                    "type": "status",
                    "message": "✅ Tüm yatırımcılar gösterildi. Yeni bir arama yapmak ister misiniz?"
                }

        elif self._should_search_investors(request.message):
            sectors = self._extract_sectors(request.message)

            yield {
                "type": "status",
                "message": f"🔍 Searching for US-based investors in {', '.join(sectors)}..."
            }

            try:
                # Request more investors for comprehensive results
                new_investors, new_search_results = await self._investor_service.find_investors(
                    sectors=sectors,
                    num_results=30,
                    enrich_profiles=True  # Enable LinkedIn enrichment
                )
                logger.info(
                    f"Found {len(new_investors)} new investors for sectors: {sectors}")

                # Store all investors in pagination state
                self._pagination_state[conversation_id]["all_investors"] = new_investors
                self._pagination_state[conversation_id]["current_page"] = 0

                # Get first page (10 investors)
                page_size = self._pagination_state[conversation_id]["page_size"]
                current_page_investors = new_investors[:page_size]

                if new_investors:
                    remaining = len(new_investors) - page_size
                    yield {
                        "type": "investors_found",
                        "count": len(new_investors),
                        "showing": len(current_page_investors),
                        "has_more": remaining > 0,
                        "remaining": remaining,
                        "investors": [inv.model_dump(mode='json') for inv in current_page_investors]
                    }
            except Exception as e:
                logger.error(f"Investor search failed: {e}")

        # Build context with memory - use current page investors for LLM
        investors_for_context = current_page_investors if current_page_investors else new_investors[
            :10]

        llm_context = self._memory_service.build_context_for_llm(
            conversation_id=conversation_id,
            new_message=request.message,
            new_investors=investors_for_context,  # Only current page for LLM
            new_search_results=new_search_results,
            new_sectors=sectors,
            max_history=20
        )

        # Get all accumulated data
        conversation = self._memory_service.get_conversation(conversation_id)
        all_investors = self._pagination_state.get(
            conversation_id, {}).get("all_investors", [])
        if not all_investors:
            all_investors = conversation.investors if conversation else new_investors
        all_search_results = conversation.search_results if conversation else new_search_results
        sectors_discussed = llm_context.get("sectors_discussed", [])

        # Determine which investors to show in response
        display_investors = current_page_investors if current_page_investors else all_investors[
            :10]

        # Stream the response
        full_response = ""
        try:
            yield {"type": "content_start"}

            async for chunk in llm_provider.generate_stream(
                messages=llm_context["messages"],
                context={
                    "conversation_id": conversation_id,
                    "investors": display_investors,  # Only current page investors
                    "total_investors": len(all_investors),
                    "search_results": llm_context["search_results"],
                    "sectors_discussed": sectors_discussed,
                    "conversation_summary": llm_context["conversation_summary"],
                    "is_pagination": is_pagination_request,
                    "current_page": self._pagination_state.get(conversation_id, {}).get("current_page", 0)
                }
            ):
                full_response += chunk
                yield {
                    "type": "content",
                    "text": chunk
                }

            # Save assistant response to memory
            self._memory_service.add_assistant_response(
                conversation_id, full_response)

        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield {
                "type": "error",
                "error": f"Error generating response: {str(e)}"
            }
            return

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Get pagination info
        state = self._pagination_state.get(conversation_id, {})
        current_page = state.get("current_page", 0)
        page_size = state.get("page_size", 10)
        total_investors = len(all_investors)
        has_more = (current_page + 1) * page_size < total_investors

        # Yield final metadata
        yield {
            "type": "done",
            "conversation_id": conversation_id,
            "sectors_discussed": sectors_discussed,
            "total_investors_found": total_investors,
            "current_page": current_page,
            "page_size": page_size,
            "has_more_investors": has_more,
            "investors": [inv.model_dump(mode='json') for inv in display_investors],
            "processing_time_ms": processing_time,
            "model_used": provider_name
        }

    def get_conversation_investors(self, conversation_id: str) -> List[InvestorProfile]:
        """Get all investors found in a conversation."""
        context = self._memory_service.get_conversation(conversation_id)
        if context:
            return context.investors
        return []

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation from memory."""
        return self._memory_service.delete_conversation(conversation_id)

    def _get_default_model(self, provider: str) -> str:
        """Get default model for a provider."""
        defaults = {
            "gemini": "gemini-pro",
            "openai": "gpt-4",
            "anthropic": "claude-3-sonnet-20240229"
        }
        return defaults.get(provider, "default")

    def _should_search_investors(self, message: str) -> bool:
        """Determine if the message requires investor search."""
        message_lower = message.lower()
        # Don't trigger search if it's a pagination request
        if self._is_pagination_request(message):
            return False
        return any(trigger in message_lower for trigger in self.SEARCH_TRIGGERS)

    def _is_pagination_request(self, message: str) -> bool:
        """Check if the user is asking for more investors (pagination)."""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.MORE_INVESTORS_TRIGGERS)

    def _extract_sectors(self, message: str) -> List[str]:
        """Extract sector keywords from user message."""
        message_lower = message.lower()
        found_sectors = []

        for sector, keywords in self.SECTOR_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                found_sectors.append(sector)

        return found_sectors if found_sectors else ["startup", "technology"]

    @staticmethod
    def list_available_providers() -> Dict[str, List[str]]:
        """List all available providers."""
        return {
            "llm": registry.list_providers("llm"),
            "search": registry.list_providers("search"),
            "scraper": registry.list_providers("scraper")
        }
