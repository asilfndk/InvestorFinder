# 🚀 AI Startup Investor Finder

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-76%20passed-success.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

**An AI-powered chatbot that helps entrepreneurs discover and connect with the right investors for their startups.**

[Features](#-features) • [Quick Start](#-quick-start) • [API](#-api-reference) • [Docker](#-docker) • [Testing](#-testing)

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
- 📥 **Export Support**: Download found investors as CSV/Excel files
- 💾 **Persistent Memory**: Remembers conversation context for better recommendations

---

## ✨ Features

### Core Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-LLM Support** | Google Gemini (default), OpenAI GPT-4, Anthropic Claude |
| 🔍 **Smart Search** | Google Custom Search API integration |
| 👤 **LinkedIn Scraping** | Extract investor profiles and details |
| 💬 **Streaming Responses** | Real-time AI responses with SSE |
| 📥 **CSV/Excel Export** | Export investor lists for offline use |
| 💾 **Conversation Memory** | SQLite-based persistent storage |
| 🔌 **Plugin Architecture** | Easily add new providers |
| 🔐 **JWT Authentication** | Secure user registration and login |
| 🧪 **Test Coverage** | 76+ unit and integration tests |

### Technical Highlights

- **API Versioning**: `/api/v1/` prefix with backward compatibility
- **Protocol-based Design**: Type-safe interfaces using Python Protocols
- **Async-first**: All I/O operations are asynchronous
- **Event-driven**: Pub/sub pattern for decoupled communication
- **Database Support**: SQLAlchemy with SQLite/PostgreSQL

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- Google Custom Search API Key (optional, for better results)

### Installation

```bash
# Clone the repository
git clone https://github.com/asilfndk/InvestorFinder.git
cd InvestorFinder

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Key Environment Variables:**

```env
# Required (for Gemini)
GEMINI_API_KEY=your_gemini_api_key

# Optional LLMs
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=gemini

# Search (Google Custom Search)
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Authentication (JWT)
JWT_SECRET_KEY=your_jwt_secret_key  # Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Running the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## 🐳 Docker

### Run with Docker Compose

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker Build

```bash
docker build -t ai-investor-finder .
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e GOOGLE_SEARCH_API_KEY=your_key \
  -e GOOGLE_SEARCH_ENGINE_ID=your_cx \
  ai-investor-finder
```

> **Note:** `docker-compose` automatically reads variables from the `.env` file.

---

## 📡 API Reference

### Base URL

All API endpoints use the `/api/v1/` prefix. Legacy `/api/` URLs are automatically redirected for backward compatibility.

### Chat Endpoints

#### Stream Chat Response
```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "Find AI investors in Silicon Valley",
  "conversation_id": "optional-uuid",
  "model_provider": "gemini"
}
```

**Response:** Server-Sent Events (SSE) stream

#### Regular Chat
```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Tell me about healthcare VCs",
  "model_provider": "gemini"
}
```

### Export Endpoints

```http
# Download investors from a conversation as CSV
GET /api/v1/export/{conversation_id}/csv

# Download investors from a conversation as Excel
GET /api/v1/export/{conversation_id}/excel
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/info` | GET | Application info |
| `/api/v1/providers` | GET | List available providers |
| `/api/v1/conversations` | GET | List all conversations |
| `/api/v1/conversation/{id}` | GET | Get conversation details |
| `/api/v1/conversation/{id}` | DELETE | Delete a conversation |

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register a new user |
| `/api/v1/auth/login` | POST | Login (returns JWT token) |
| `/api/v1/auth/me` | GET | Get current user (requires token) |
| `/api/v1/auth/refresh` | POST | Refresh token (requires token) |

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_chat_service.py` | 18 | Sector extraction, search triggers, pagination |
| `test_investor_service.py` | 8 | Cache key generation, pagination |
| `test_memory_service.py` | 19 | Conversation context, serialization |
| `test_routes.py` | 12 | API endpoint validations |
| `test_auth.py` | 9 | Authentication endpoints |
| `test_health.py` | 1 | Health check |

**Total: 76 tests ✅**

---

## 🏗️ Project Structure

```
InvestorFinder/
├── app/
│   ├── core/            # Protocols, provider registry, events
│   ├── database/        # SQLAlchemy models, repositories
│   ├── providers/       # LLM/search/scraper implementations
│   │   ├── llm/         # Gemini, OpenAI, Anthropic
│   │   ├── search/      # Google Search
│   │   └── scraper/     # LinkedIn scraper
│   ├── models/          # Pydantic schemas
│   ├── services/        # Business logic
│   ├── routes/          # FastAPI routers
│   │   ├── chat.py      # Chat endpoints
│   │   └── export.py    # Export endpoints
│   ├── config.py        # Settings
│   └── main.py          # FastAPI app
├── static/              # Frontend UI
├── tests/               # Unit & integration tests
├── data/                # Local storage (gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google Gemini API key (required) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `DEFAULT_LLM_PROVIDER` | `gemini` | Default LLM provider |
| `GOOGLE_SEARCH_API_KEY` | - | Google Custom Search key |
| `GOOGLE_SEARCH_ENGINE_ID` | - | Search Engine ID |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per minute |
| `DEBUG` | `true` | Debug mode |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write tests for new features
- Update documentation as needed

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

[Report Bug](https://github.com/asilfndk/InvestorFinder/issues) • [Request Feature](https://github.com/asilfndk/InvestorFinder/issues)

</div>
