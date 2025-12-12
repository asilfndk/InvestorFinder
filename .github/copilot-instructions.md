# AI Startup Investor Finder Chatbot

## Project Overview

This is an AI chatbot application that helps entrepreneurs find investors.
Built with a professional, modular, and extensible architecture.

## Architecture Principles

- **Protocol-based Design**: Type-safe interfaces using Python Protocols
- **Plugin Architecture**: New providers can be easily added
- **Registry Pattern**: Simple decorator-based provider registration
- **Event-Driven**: Pub/sub pattern for decoupled communication
- **Async-first**: All I/O operations are asynchronous

## Tech Stack

- **Backend**: Python 3.10+, FastAPI
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **AI**: Google Gemini API (default), OpenAI (optional)
- **Web Scraping**: BeautifulSoup, httpx
- **Search**: Google Custom Search API

## Project Structure

```
app/
├── core/           # Protocols, exceptions, events, providers
├── database/       # SQLAlchemy models and repositories
├── providers/      # LLM, search, scraper implementations
│   ├── llm/        # Gemini, OpenAI
│   ├── search/     # Google Search
│   └── scraper/    # LinkedIn
├── models/         # Pydantic schemas
├── services/       # Business logic
└── routes/         # API endpoints
```

## Adding New Provider

1. Create a new file in `app/providers/<type>/`
2. Implement the Protocol from `app/core/protocols.py`
3. Use `@register` decorator from `app/core/providers.py`
4. Import in `app/providers/<type>/__init__.py`
5. Add required API keys to `.env`

Example:

```python
from app.core.protocols import LLMProvider, LLMConfig, ProviderMixin
from app.core.providers import register

@register("llm", "my_provider")
class MyProvider(ProviderMixin):
    async def initialize(self) -> None: ...
    async def generate_response(self, messages, context) -> str: ...
    async def generate_stream(self, messages, context): ...
    async def cleanup(self) -> None: ...
```

## Development Notes

- Store API keys in `.env` file
- All providers should implement Protocols from `app/core/protocols.py`
- Use `get_llm()`, `get_search()`, `get_scraper()` factory functions
- Use event bus for inter-service communication
- All async operations use asyncio
- Focus on US-based investors (Silicon Valley, NYC, Boston, etc.)
- All prompts and responses in English
