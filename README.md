# 🚀 AI Startup Investor Finder

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-67%20passed-success.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

**AI destekli chatbot ile startup'ınız için doğru yatırımcıları bulun.**

[Özellikler](#-özellikler) • [Hızlı Başlangıç](#-hızlı-başlangıç) • [API](#-api-referansı) • [Docker](#-docker) • [Test](#-test)

</div>

---

## 📋 Genel Bakış

AI Startup Investor Finder, girişimcilerin sektör, aşama ve konum tercihlerine göre uygun yatırımcıları bulmalarına yardımcı olan akıllı bir chatbot uygulamasıdır. Sistem, ABD merkezli yatırımcıları (Silicon Valley, NYC, Boston vb.) arar ve iletişim bilgileriyle detaylı profiller sunar.

### Neden Bu Proje?

Doğru yatırımcıyı bulmak startup'lar için en büyük zorluklardan biridir. Bu araç araştırma sürecini otomatikleştirerek:

- 🔍 **Akıllı Arama**: Google Custom Search ile ilgili yatırımcı profillerini bulur
- 🤖 **AI Destekli Analiz**: Gemini/OpenAI ile ihtiyaçlarınızı anlar ve yatırımcıları eşleştirir
- 📊 **Zengin Profiller**: LinkedIn'den detaylı yatırımcı bilgilerini çeker
- 💬 **Konuşma Arayüzü**: Kolay etkileşim için doğal sohbet arayüzü
- 📥 **Export Desteği**: Bulunan yatırımcıları CSV/Excel olarak indirin
- 💾 **Kalıcı Hafıza**: Daha iyi öneriler için konuşma bağlamını hatırlar

---

## ✨ Özellikler

### Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🤖 **Çoklu LLM Desteği** | Google Gemini (varsayılan), OpenAI GPT-4, Anthropic Claude |
| 🔍 **Akıllı Arama** | Google Custom Search API entegrasyonu |
| 👤 **LinkedIn Scraping** | Yatırımcı profilleri ve detaylarını çıkarma |
| 💬 **Streaming Yanıtlar** | SSE ile gerçek zamanlı AI yanıtları |
| 📥 **CSV/Excel Export** | Yatırımcı listelerini dışa aktarma |
| 💾 **Konuşma Hafızası** | SQLite tabanlı kalıcı depolama |
| 🔌 **Plugin Mimarisi** | Kolayca yeni provider'lar ekleme |
| 🧪 **Test Coverage** | 67+ unit ve integration test |

### Teknik Özellikler

- **API Versioning**: `/api/v1/` prefix ile versiyonlu API
- **Protocol-based Design**: Python Protocols ile tip güvenli arayüzler
- **Async-first**: Tüm I/O işlemleri asenkron
- **Event-driven**: Pub/sub pattern ile bileşenler arası iletişim
- **Database**: SQLAlchemy ile SQLite/PostgreSQL desteği

---

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.10+
- Google Gemini API Key ([Buradan alın](https://makersuite.google.com/app/apikey))
- Google Custom Search API Key (isteğe bağlı)

### Kurulum

```bash
# Repository'yi klonlayın
git clone https://github.com/asilfndk/InvestorFinder.git
cd InvestorFinder

# Virtual environment oluşturun
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# veya
.\.venv\Scripts\activate  # Windows

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### Yapılandırma

```bash
# Environment dosyasını kopyalayın
cp .env.example .env

# .env dosyasını düzenleyin
nano .env
```

**Temel Environment Değişkenleri:**

```env
# Zorunlu (Gemini için)
GEMINI_API_KEY=your_gemini_api_key

# İsteğe Bağlı LLM'ler
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=gemini

# Search (Google Custom Search)
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

### Uygulamayı Çalıştırma

```bash
# Development modu (auto-reload ile)
uvicorn app.main:app --reload --port 8000

# Production modu
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Tarayıcınızda **http://localhost:8000** adresini açın.

---

## 🐳 Docker

### Docker Compose ile Çalıştırma

```bash
# Build ve başlatma
docker-compose up -d --build

# Logları görüntüleme
docker-compose logs -f

# Durdurma
docker-compose down
```

### Manuel Docker Build

```bash
docker build -t ai-investor-finder .
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e GOOGLE_SEARCH_API_KEY=your_key \
  -e GOOGLE_SEARCH_ENGINE_ID=your_cx \
  ai-investor-finder
```

> **Not:** `docker-compose`, `.env` dosyasındaki değişkenleri otomatik okur.

---

## 📡 API Referansı

### Base URL

Tüm API endpoint'leri `/api/v1/` prefix'i kullanır. Eski `/api/` URL'leri backward compatibility için otomatik yönlendirilir.

### Chat Endpoint'leri

#### Stream Chat Response
```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "AI alanında Silicon Valley yatırımcıları bul",
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
  "message": "Healthcare VC'leri hakkında bilgi ver",
  "model_provider": "gemini"
}
```

### Export Endpoint'leri

```http
# Konuşmadaki yatırımcıları CSV olarak indir
GET /api/v1/export/{conversation_id}/csv

# Konuşmadaki yatırımcıları Excel olarak indir
GET /api/v1/export/{conversation_id}/excel
```

### Diğer Endpoint'ler

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/health` | GET | Health check |
| `/info` | GET | Uygulama bilgisi |
| `/api/v1/providers` | GET | Mevcut provider'ları listele |
| `/api/v1/conversations` | GET | Tüm konuşmaları listele |
| `/api/v1/conversation/{id}` | GET | Konuşma detayları |
| `/api/v1/conversation/{id}` | DELETE | Konuşmayı sil |

---

## 🧪 Test

### Testleri Çalıştırma

```bash
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage ile çalıştır
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Test Coverage

| Test Dosyası | Test Sayısı | Açıklama |
|--------------|-------------|----------|
| `test_chat_service.py` | 18 | Sector extraction, search triggers, pagination |
| `test_investor_service.py` | 8 | Cache key, pagination |
| `test_memory_service.py` | 19 | Conversation context, serialization |
| `test_routes.py` | 12 | API endpoint validations |
| `test_health.py` | 1 | Health check |

**Toplam: 67 test ✅**

---

## 🏗️ Proje Yapısı

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

## 🔧 Yapılandırma Seçenekleri

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `GEMINI_API_KEY` | - | Google Gemini API key (zorunlu) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `DEFAULT_LLM_PROVIDER` | `gemini` | Varsayılan LLM provider |
| `GOOGLE_SEARCH_API_KEY` | - | Google Custom Search key |
| `GOOGLE_SEARCH_ENGINE_ID` | - | Search Engine ID |
| `RATE_LIMIT_PER_MINUTE` | `30` | Dakika başına rate limit |
| `DEBUG` | `true` | Debug modu |

---

## 🤝 Katkıda Bulunma

1. Repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/YeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'i push edin (`git push origin feature/YeniOzellik`)
5. Pull Request açın

### Geliştirme Kuralları

- PEP 8 stil kılavuzuna uyun
- Tüm fonksiyonlara type hints ekleyin
- Yeni özellikler için test yazın
- Dokümantasyonu güncelleyin

---

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI language model
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

---

<div align="center">

**Girişimciler için ❤️ ile yapıldı**

[Bug Bildir](https://github.com/asilfndk/InvestorFinder/issues) • [Özellik İste](https://github.com/asilfndk/InvestorFinder/issues)

</div>
