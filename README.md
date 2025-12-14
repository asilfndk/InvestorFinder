# 🚀 AI Startup Investor Finder

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

**An AI-powered chatbot that helps entrepreneurs discover and connect with the right investors for their startups.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API](#-api-reference) • [Contributing](#-contributing)

</div>

---

## 📋 Overview

AI Startup Investor Finder is an intelligent chatbot application that leverages AI to help entrepreneurs find suitable investors based on their startup's sector, stage, and location preferences. The system searches for US-based investors (Silicon Valley, NYC, Boston, etc.) and provides detailed profiles with contact information.

### Why This Project?

Finding the right investor is one of the biggest challenges for startups. This tool automates the research process by:

- 🔍 **Intelligent Search**: Uses Google Custom Search to find relevant investor profiles
- 🤖 **AI-Powered Analysis**: Leverages Gemini/OpenAI to understand your needs and match investors
- 📊 **Rich Profiles**: Scrapes LinkedIn for detailed investor information
- 💬 **Conversational UI**: Natural chat interface for easy interaction
- 💾 **Persistent Memory**: Remembers conversation context for better recommendations

---

## ✨ Features

### Core Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-LLM Support** | Google Gemini (default), OpenAI GPT-4 |
| 🔍 **Smart Search** | Google Custom Search API integration |
| 👤 **LinkedIn Scraping** | Extract investor profiles and details |
| 💬 **Streaming Responses** | Real-time AI responses with SSE |
| 📧 **Email Extraction** | Find investor contact information |
| 💾 **Conversation Memory** | SQLite-based persistent storage |
| 🔌 **Plugin Architecture** | Easily add new providers |

### Technical Highlights

- **Protocol-based Design**: Type-safe interfaces using Python Protocols
- **Async-first**: All I/O operations are asynchronous
- **Event-driven**: Pub/sub pattern for decoupled communication
- **Database Storage**: SQLAlchemy with SQLite/PostgreSQL support
- **Modern Python**: Type hints, dataclasses, and async/await

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- Google Custom Search API Key (optional, for better results)

### Installation

```bash
# Clone the repository
git clone https://github.com/asilfndk/ai-investor-finder.git
cd ai-investor-finder

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for advanced scraping)
playwright install chromium
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Environment Variables (key ones):**

```env
# Required for Gemini (default)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional LLMs
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEFAULT_LLM_PROVIDER=gemini  # gemini | openai | anthropic

# Search (Google Custom Search)
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# CORS & logging
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
LOG_JSON=false

# LLM fallback & provider cooldown
LLM_FALLBACK_ORDER=gemini,openai,anthropic
PROVIDER_FAILURE_COOLDOWN_SECONDS=300

# Scraping
LINKEDIN_SCRAPE_DELAY=0.2
LINKEDIN_MAX_CONCURRENCY=3
LINKEDIN_MIN_DELAY=1.5
LINKEDIN_MAX_DELAY=4.0
LINKEDIN_PROXY=
LINKEDIN_PROXIES=
PLAYWRIGHT_ENABLED=false
PLAYWRIGHT_HEADLESS=true

# Search behavior
SEARCH_TIMEOUT_SECONDS=15
SEARCH_MAX_RETRIES=2
SEARCH_CACHE_TTL_MINUTES=20
```

### Running the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### 🐳 Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t ai-investor-finder .
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e GOOGLE_SEARCH_API_KEY=your_key \
  -e GOOGLE_SEARCH_ENGINE_ID=your_cx \
  -e DEFAULT_LLM_PROVIDER=gemini \
  ai-investor-finder
```

> Not: `docker-compose` `.env` dosyasındaki değişkenleri otomatik okur (GEMINI/OPENAI/ANTHROPIC ve Google arama, scrape, log ayarları).

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🏗️ Architecture

### Project Structure

```
ai-investor-finder/
├── app/
│   ├── core/                    # Core components
│   │   ├── protocols.py         # Type-safe Protocol interfaces
│   │   ├── providers.py         # Provider registry & factory
│   │   ├── events.py            # Event bus (pub/sub)
│   │   └── exceptions.py        # Custom exceptions
│   │
│   ├── database/                # Database layer
│   │   ├── connection.py        # Async SQLAlchemy connection
│   │   ├── models.py            # ORM models
│   │   └── repositories.py      # Data access layer
│   │
│   ├── providers/               # Plugin-based providers
│   │   ├── llm/                 # LLM providers
│   │   │   ├── gemini.py        # Google Gemini
│   │   │   └── openai_provider.py
│   │   ├── search/              # Search providers
│   │   │   └── google.py        # Google Custom Search
│   │   └── scraper/             # Web scrapers
│   │       └── linkedin.py      # LinkedIn scraper
│   │
│   ├── models/                  # Pydantic schemas
│   │   └── schemas.py           # Request/Response models
│   │
│   ├── services/                # Business logic
│   │   ├── chat_service.py      # Chat orchestration
│   │   ├── investor_service.py  # Investor search
│   │   └── memory_service.py    # Conversation memory
│   │
│   ├── routes/                  # API endpoints
│   │   └── chat.py              # Chat API routes
│   │
│   ├── config.py                # Configuration
│   └── main.py                  # FastAPI application
│
├── static/                      # Frontend assets
│   └── index.html               # Chat UI
│
├── data/                        # Data storage (gitignored)
│   ├── conversations/           # JSON conversation files
│   └── investor_finder.db       # SQLite database
│
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

### Provider System

The application uses a plugin architecture that makes it easy to add new providers:

```python
from app.core.protocols import LLMProvider, ProviderMixin
from app.core.providers import register

@register("llm", "my_provider")
class MyLLMProvider(ProviderMixin):
    """Custom LLM provider."""
    
    async def initialize(self) -> None:
        # Setup API client
        pass
    
    async def generate_response(self, messages: list, context: str | None = None) -> str:
        # Generate response
        pass
    
    async def generate_stream(self, messages: list, context: str | None = None):
        # Stream response chunks
        yield "chunk"
    
    async def cleanup(self) -> None:
        # Cleanup resources
        pass
```

### Database Schema

```
┌─────────────────┐     ┌─────────────────┐
│  conversations  │────<│    messages     │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │
│ title           │     │ conversation_id │
│ created_at      │     │ role            │
│ updated_at      │     │ content         │
│ metadata        │     │ timestamp       │
└─────────────────┘     └─────────────────┘
         │
         │              ┌─────────────────┐
         └─────────────<│    investors    │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ name            │
                        │ title           │
                        │ company         │
                        │ linkedin_url    │
                        │ sectors         │
                        │ location        │
                        └─────────────────┘
```

---

## 📡 API Reference

### Chat Endpoints

#### Stream Chat Response

```http
POST /api/chat/stream
Content-Type: application/json

{
  "message": "Find AI investors in Silicon Valley",
  "conversation_id": "optional-uuid",
  "model_provider": "gemini"
}
```

**Response**: Server-Sent Events (SSE) stream

Quick SSE example in JavaScript:

```js
const res = await fetch("/api/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "Find AI investors in Silicon Valley",
    model_provider: "gemini" // or "openai"
  })
});

const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  for (const block of buffer.split("\n\n")) {
    if (!block.startsWith("data: ")) continue;
    const payload = JSON.parse(block.slice(6));
    console.log(payload.type, payload);
  }
  buffer = "";
}
```

#### Regular Chat Response

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Tell me about healthcare VCs",
  "model_provider": "gemini"
}
```

### Provider Endpoints

#### List Available Providers

```http
GET /api/providers
```

**Response**:
```json
{
  "llm": ["gemini", "openai", "anthropic"],
  "search": ["google"],
  "scraper": ["linkedin"]
}
```

### Conversation Endpoints

#### Get Conversation History

```http
GET /api/conversations/{conversation_id}
```

#### List All Conversations

```http
GET /api/conversations
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `OPENAI_API_KEY` | No | - | OpenAI API key |
| `GOOGLE_SEARCH_API_KEY` | No | - | Google Custom Search key |
| `GOOGLE_SEARCH_ENGINE_ID` | No | - | Search Engine ID |
| `DEFAULT_LLM_PROVIDER` | No | `gemini` | Default LLM provider |
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LINKEDIN_SCRAPE_DELAY` | No | `2` | Delay between scrapes (seconds) |

### Adding a New LLM Provider

1. Create a new file in `app/providers/llm/`:

```python
# app/providers/llm/anthropic.py
from app.core.protocols import LLMProvider, ProviderMixin
from app.core.providers import register

@register("llm", "anthropic")
class AnthropicProvider(ProviderMixin):
    async def initialize(self) -> None:
        import anthropic
        self.client = anthropic.AsyncClient()
    
    async def generate_response(self, messages, context=None) -> str:
        response = await self.client.messages.create(
            model="claude-3-sonnet-20240229",
            messages=messages
        )
        return response.content[0].text
    
    async def generate_stream(self, messages, context=None):
        async with self.client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def cleanup(self) -> None:
        pass
```

2. Import in `app/providers/llm/__init__.py`:

```python
from .anthropic import AnthropicProvider
```

3. Add API key to `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
```

---

## 🧪 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Type checking
mypy app/

# Lint
ruff check app/
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public APIs
- Include tests for new features
- Update documentation as needed

---

## ⚠️ Important Notes

1. **API Keys**: Never commit your `.env` file
2. **LinkedIn Scraping**: Apply rate limiting to avoid being blocked
3. **Production**: Set `DEBUG=false` and configure CORS properly
4. **Focus Area**: Currently optimized for US-based investors

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI language model
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

---

<div align="center">

**Built with ❤️ for Entrepreneurs**

[Report Bug](https://github.com/asilfndk/ai-investor-finder/issues) • [Request Feature](https://github.com/asilfndk/ai-investor-finder/issues)

</div>
