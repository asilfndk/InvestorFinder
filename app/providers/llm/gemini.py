"""
Gemini LLM Provider implementation.
Modern Protocol-based approach with backward compatibility.
"""

import asyncio
import google.generativeai as genai
from typing import List, Optional, Dict, Any, AsyncIterator
import logging

from app.core.protocols import LLMConfig, ProviderMixin
from app.core.providers import register
from app.core.exceptions import LLMProviderError
from app.models import ChatMessage, MessageRole
from app.config import get_settings

logger = logging.getLogger(__name__)


@register("llm", "gemini")
class GeminiProvider(ProviderMixin):
    """
    Google Gemini LLM provider implementation.

    Implements the LLMProvider protocol without inheritance.
    Uses ProviderMixin for common functionality.
    """

    # Default system prompt for investor finding
    DEFAULT_SYSTEM_PROMPT = """You are a concise, factual startup investor finder assistant.

Goals:
1) Understand the startup’s sector + stage + location preference (use user/location context if provided; otherwise prefer US/major hubs but do NOT fabricate location filters).
2) List up to 10 investors per response, with clear pagination: if more exist, state how many remain and ask the user to say "more" or "show more investors" to continue.
3) For each investor, show: Name, Title, Company, Location, Investment Focus, Bio (max ~2 sentences), LinkedIn URL. Do not invent missing fields; leave them blank/omit if unknown.
4) Keep tone professional, non-salesy, and action-oriented.
5) If the user’s message language is not English, respond in that language; otherwise default to English. Keep investor data as-is.

Output format (markdown list):
1. **Name**
   Title @ Company
   Location: <city/region or "—" if unknown>
   Focus: tag1, tag2 (omit if unknown)
   Bio: short, 1–2 sentences
   LinkedIn: URL (omit if unknown)

Rules:
- Never show more than 10 investors in one response.
- Do not promise future actions; share what you have now.
- Highlight remaining count if more investors are available.
- Keep paragraphs short (max 2–3 sentences overall).
- Respect user location if given; otherwise US-first but not US-only.
- Be explicit and avoid filler phrases.
"""

    def __init__(self, config: LLMConfig):
        super().__init__()  # Initialize ProviderMixin
        self._config = config
        self._model = None
        self._chat_sessions: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        """Provider name for Protocol compliance."""
        return "gemini"

    @property
    def provider_name(self) -> str:
        """Backward compatible property."""
        return self.name

    @property
    def config(self) -> LLMConfig:
        return self._config

    async def initialize(self) -> None:
        """Initialize Gemini API."""
        try:
            settings = get_settings()
            genai.configure(api_key=settings.gemini_api_key)

            model_name = self._config.model_name or "gemini-pro"
            self._model = genai.GenerativeModel(model_name)

            self.mark_initialized()  # Use mixin method
            logger.info(
                f"Gemini provider initialized with model: {model_name}")

        except Exception as e:
            self.record_error()  # Use mixin method
            raise LLMProviderError(
                message=f"Failed to initialize Gemini: {str(e)}",
                provider="gemini",
                original_error=e
            )

    def _get_or_create_session(self, conversation_id: str) -> Any:
        """Get or create a chat session."""
        if conversation_id not in self._chat_sessions:
            self._chat_sessions[conversation_id] = self._model.start_chat(
                history=[])
        return self._chat_sessions[conversation_id]

    def _build_prompt(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt from messages and context with memory support."""
        parts = []

        # Add system prompt
        system_prompt = self._config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        parts.append(system_prompt)

        # Add conversation summary if available (from memory)
        if context and context.get("conversation_summary"):
            summary = context["conversation_summary"]
            if summary.get("sectors_discussed"):
                parts.append(
                    f"\n\n📌 Sectors discussed in conversation: {', '.join(summary['sectors_discussed'])}")
            if summary.get("investors_found", 0) > 0:
                parts.append(
                    f"📌 Total investors found so far: {summary['investors_found']}")

        # Add sectors discussed for context continuity
        if context and context.get("sectors_discussed"):
            parts.append(
                f"\n\n🎯 User's sectors of interest: {', '.join(context['sectors_discussed'])}")

        # Add search results if provided
        if context and context.get("search_results"):
            search_results = context["search_results"]
            parts.append(
                f"\n\n🔍 Web search results ({len(search_results)} results):")
            for result in search_results[:15]:  # Show more results
                parts.append(
                    f"- {result.title}: {result.snippet[:150]}...")

        # Add investors for this page (10 at a time)
        if context and context.get("investors"):
            investors = context["investors"]
            total_count = context.get("total_investors", len(investors))
            current_page = context.get("current_page", 0)
            is_pagination = context.get("is_pagination", False)

            if is_pagination:
                parts.append(
                    f"\n\n👥 Next investors (page {current_page + 1}, showing {len(investors)} on this page, {total_count} total):")
            else:
                parts.append(
                    f"\n\n👥 Found investors (showing {len(investors)} on this page, {total_count} total):")

            for inv in investors:  # Only current page investors
                inv_info = f"\n### {inv.name}"
                if inv.title:
                    inv_info += f"\n   📌 Title: {inv.title}"
                if inv.company:
                    inv_info += f"\n   🏢 Company: {inv.company}"
                if hasattr(inv, 'location') and inv.location:
                    inv_info += f"\n   📍 Location: {inv.location}"
                if hasattr(inv, 'bio') and inv.bio:
                    bio_short = inv.bio[:200] + \
                        "..." if len(inv.bio) > 200 else inv.bio
                    inv_info += f"\n   📝 Bio: {bio_short}"
                if hasattr(inv, 'investment_focus') and inv.investment_focus:
                    inv_info += f"\n   🎯 Investment Focus: {', '.join(inv.investment_focus)}"
                if inv.linkedin_url:
                    inv_info += f"\n   🔗 LinkedIn: {inv.linkedin_url}"
                parts.append(inv_info)

            if total_count > len(investors):
                remaining = total_count - (current_page + 1) * 10
                if remaining > 0:
                    parts.append(
                        f"\n\n📢 {remaining} more investors available. If user says 'more' or 'show more investors', show next 10.")

        # Add conversation history for context
        parts.append("\n\n💬 Conversation history:")
        for msg in messages:
            role_label = "User" if msg.role == MessageRole.USER else "Assistant"
            parts.append(f"{role_label}: {msg.content}")

        return "\n".join(parts)

    async def generate_response(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response from Gemini."""
        if not self.is_initialized:
            raise LLMProviderError(
                message="Provider not initialized",
                provider="gemini"
            )

        try:
            self.record_request()  # Track usage
            conversation_id = context.get(
                "conversation_id", "default") if context else "default"
            chat = self._get_or_create_session(conversation_id)

            prompt = self._build_prompt(messages, context)
            response = chat.send_message(prompt)

            return response.text

        except Exception as e:
            self.record_error()
            logger.error(f"Gemini generation error: {e}")
            raise LLMProviderError(
                message=f"Generation failed: {str(e)}",
                provider="gemini",
                original_error=e
            )

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Gemini."""
        if not self.is_initialized:
            raise LLMProviderError(
                message="Provider not initialized",
                provider="gemini"
            )

        try:
            self.record_request()  # Track usage
            conversation_id = context.get(
                "conversation_id", "default") if context else "default"
            chat = self._get_or_create_session(conversation_id)

            prompt = self._build_prompt(messages, context)
            response = chat.send_message(prompt, stream=True)

            # Gemini returns a sync iterator, yield chunks with delay for better UX
            for chunk in response:
                if chunk.text:
                    # Split chunk into smaller pieces for smoother streaming effect
                    text = chunk.text
                    # Yield character by character for very smooth effect
                    chunk_size = 3  # Characters per yield
                    for i in range(0, len(text), chunk_size):
                        yield text[i:i+chunk_size]
                        # Delay for typing effect - 30ms per chunk
                        await asyncio.sleep(0.03)

        except Exception as e:
            self.record_error()
            logger.error(f"Gemini streaming error: {e}")
            raise LLMProviderError(
                message=f"Streaming failed: {str(e)}",
                provider="gemini",
                original_error=e
            )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._chat_sessions.clear()
        self._state.initialized = False
        logger.info("Gemini provider cleaned up")
