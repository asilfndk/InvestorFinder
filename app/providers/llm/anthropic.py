"""
Anthropic (Claude) LLM Provider implementation.
Uses the same structured prompt as other providers for consistency.
"""

import logging
import os
from typing import List, Optional, Dict, Any, AsyncIterator

from app.core.protocols import LLMConfig, ProviderMixin
from app.core.providers import register
from app.core.exceptions import LLMProviderError, ConfigurationError
from app.models import ChatMessage

logger = logging.getLogger(__name__)


@register("llm", "anthropic")
class AnthropicProvider(ProviderMixin):
    """
    Anthropic Claude LLM provider implementation.
    """

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

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            temperature=0.7,
            max_tokens=2048
        )
        self._client = None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def initialize(self) -> None:
        """Initialize Anthropic client."""
        if self._initialized:
            return
        try:
            from anthropic import AsyncAnthropic

            api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY not found in environment variables"
                )

            self._client = AsyncAnthropic(api_key=api_key)
            self._initialized = True
            logger.info(
                f"Anthropic provider initialized with model: {self.config.model_name}")
        except ImportError:
            raise ConfigurationError(
                "Anthropic package not installed. Run: pip install anthropic"
            )
        except Exception as e:
            raise LLMProviderError(
                message=f"Failed to initialize Anthropic: {str(e)}",
                provider="anthropic",
                original_error=e
            )

    def _build_messages(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Build Anthropic message format."""
        system_content = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT

        # Include lightweight context inline in the system message
        if context:
            if context.get("sectors_discussed"):
                system_content += f"\n\nSectors discussed: {', '.join(context['sectors_discussed'])}"
            if context.get("investors"):
                system_content += f"\n\nInvestors in context: {len(context['investors'])} (show at most 10)."

        claude_messages = [{"role": "system", "content": system_content}]
        for msg in messages:
            claude_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return claude_messages

    async def generate_response(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response from Anthropic."""
        if not self._initialized or not self._client:
            await self.initialize()

        try:
            claude_messages = self._build_messages(messages, context)
            resp = await self._client.messages.create(
                model=self.config.model_name or "claude-3-sonnet-20240229",
                messages=claude_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            # Anthropic returns content as a list of blocks
            return "".join(block.text for block in resp.content if hasattr(block, "text"))
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise LLMProviderError(
                message=f"Generation failed: {str(e)}",
                provider="anthropic",
                original_error=e
            )

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Anthropic."""
        if not self._initialized or not self._client:
            await self.initialize()

        try:
            claude_messages = self._build_messages(messages, context)
            async with self._client.messages.stream(
                model=self.config.model_name or "claude-3-sonnet-20240229",
                messages=claude_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            ) as stream:
                async for event in stream:
                    if hasattr(event, "text") and event.text:
                        yield event.text
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise LLMProviderError(
                message=f"Streaming failed: {str(e)}",
                provider="anthropic",
                original_error=e
            )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._client = None
        self._initialized = False
