"""
OpenAI LLM Provider implementation.
Ready-to-use template for OpenAI integration.
Uses modern Protocol-based architecture.
"""

from typing import List, Optional, Dict, Any, AsyncIterator
import logging
import os

from app.core.protocols import LLMProvider, LLMConfig, ProviderMixin
from app.core.providers import register
from app.core.exceptions import LLMProviderError, ConfigurationError
from app.models import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


@register("llm", "openai")
class OpenAIProvider(ProviderMixin):
    """
    OpenAI LLM provider implementation.

    To use this provider:
    1. Install openai package: pip install openai
    2. Set OPENAI_API_KEY in .env
    3. Select 'openai' as model_provider in chat request
    """

    DEFAULT_SYSTEM_PROMPT = """You are an AI assistant specialized in helping entrepreneurs find investors.

Your responsibilities:
1. Understand the user's startup sector and needs
2. Search for relevant investors using web search
3. Gather information from LinkedIn profiles
4. Find email addresses when possible
5. Organize and present investor recommendations

Guidelines:
- Focus on US-based investors (Silicon Valley, NYC, Boston, etc.)
- Always respond in English
- Be professional and helpful
- Present information in a clear, organized manner
"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            temperature=0.7,
            max_tokens=2048
        )
        self._client = None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "openai"

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        if self._initialized:
            return

        try:
            # Lazy import to avoid requiring openai package if not used
            from openai import AsyncOpenAI

            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "OPENAI_API_KEY not found in environment variables"
                )

            self._client = AsyncOpenAI(api_key=api_key)
            self._initialized = True

            logger.info(
                f"OpenAI provider initialized with model: {self.config.model_name}")

        except ImportError:
            raise ConfigurationError(
                "OpenAI package not installed. Run: pip install openai"
            )
        except Exception as e:
            raise LLMProviderError(
                message=f"Failed to initialize OpenAI: {str(e)}",
                provider="openai",
                original_error=e
            )

    def _build_messages(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Build OpenAI message format."""
        openai_messages = []

        # Add system message
        system_content = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT

        # Add context to system message
        if context:
            if context.get("search_results"):
                system_content += "\n\nWeb search results:"
                for result in context["search_results"][:5]:
                    system_content += f"\n- {result.title}: {result.snippet}"

            if context.get("investors"):
                system_content += "\n\nInvestors found:"
                for inv in context["investors"]:
                    inv_info = f"\n- {inv.name}"
                    if inv.title:
                        inv_info += f" | {inv.title}"
                    if inv.company:
                        inv_info += f" at {inv.company}"
                    if inv.email:
                        inv_info += f" | Email: {inv.email}"
                    system_content += inv_info

        openai_messages.append({
            "role": "system",
            "content": system_content
        })

        # Add conversation messages
        for msg in messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return openai_messages

    async def generate_response(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response from OpenAI."""
        if not self._initialized or not self._client:
            await self.initialize()

        try:
            openai_messages = self._build_messages(messages, context)

            response = await self._client.chat.completions.create(
                model=self.config.model_name or "gpt-4",
                messages=openai_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise LLMProviderError(
                message=f"Generation failed: {str(e)}",
                provider="openai",
                original_error=e
            )

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Generate a streaming response from OpenAI."""
        if not self._initialized or not self._client:
            await self.initialize()

        try:
            openai_messages = self._build_messages(messages, context)

            stream = await self._client.chat.completions.create(
                model=self.config.model_name or "gpt-4",
                messages=openai_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise LLMProviderError(
                message=f"Streaming failed: {str(e)}",
                provider="openai",
                original_error=e
            )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._client = None
        self._initialized = False
        logger.info("OpenAI provider cleaned up")
