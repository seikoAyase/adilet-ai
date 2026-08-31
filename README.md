# 🇰🇿 KZ Legal RAG — AI Legal Assistant for Kazakhstan Legislation

A production-oriented, agentic **Retrieval-Augmented Generation (RAG)** system designed to search, cite, and answer questions based on the official legislation and legal codes of the Republic of Kazakhstan (sourced from the official legal information system [ИС «Әділет» / zan.kz](https://adilet.zan.kz)).

---

## 🌟 Key Features

- **Hierarchical Legal Parser (State Machine):** Automatically parses raw HTML legislation while preserving full statutory hierarchy (`Section -> Chapter -> Article -> Clause`).
- **Context Injection (Breadcrumbs):** Injects hierarchical breadcrumbs into each article embedding to distinguish identically structured norms across different codes.
- **PostgreSQL + pgvector with HNSW Indexing:** Ultra-fast, low-latency approximate nearest neighbor (ANN) vector search directly inside PostgreSQL.
- **Autonomous Tool Calling (Agentic Routing):** Powered by **Google Gemini 2.5 Flash** Function Calling. The agent autonomously classifies user intent, selects relevant statutory codes (`koap_rk`, `tk_rk`, `uk_rk`, `consumer_rights`, `too_law`), reformulates queries into legal terminology, and retrieves articles.
- **Local Multilingual Embeddings:** High-performance ONNX-based dense vector embeddings via **FastEmbed** (`paraphrase-multilingual-MiniLM-L12-v2`), with zero external embedding API costs and native Russian/Kazakh support.
- **Strict Anti-Hallucination Grounding & Citations:** Structured responses with verified citations (`[1]`, `[2]`), article numbers, code titles, and direct links to official sources on `adilet.zan.kz`.
- **Async Production Backend:** Built on **FastAPI**, **SQLAlchemy 2.0 (asyncio)**, **asyncpg**, **Alembic**, and **Pydantic v2**.

---

## 🏗️ Architecture Workflow

```text
===================================================================================================
                                      KZ LEGAL RAG ARCHITECTURE
===================================================================================================

[ 1. OFFLINE INGESTION PIPELINE ]
  ИС «Әділет» (adilet.zan.kz) HTML
            │
            ▼
    [ Legal Parser (State Machine) ] ──► [ Article Hierarchy Extraction ]
                                                       │
                                                       ├──────────────────────────┐
                                                       ▼                          ▼
                                            [ FastEmbed (ONNX) ]         [ Metadata & Raw Text ]
                                                       │                          │
                                                       ▼                          ▼
                                            [ PostgreSQL + pgvector ]   [ Document / Chunk Tables ]
                                             (384-dim, HNSW Index)

───────────────────────────────────────────────────────────────────────────────────────────────────

[ 2. ONLINE AGENTIC INFERENCE PIPELINE ]

      [ User / Client Query ]
                 │ (HTTP POST /api/v1/chat)
                 ▼
      [ FastAPI Gateway ]
                 │
                 ▼
      [ Google Gemini Agent ] ── (Autonomous Decision) ──► [ Tool: search_legislation ]
                 │                                                │
                 │                                                ├─► Auto-selects code (e.g. koap_rk)
                 │                                                └─► Rewrites to legal query
                 │                                                                │
                 │                                                                ▼
                 │                                                    [ pgvector Cosine Search ]
                 │                                                                │ (Top-K Chunks)
                 ▼                                                                │
      [ Grounded LLM Generation ] ◄───────────────────────────────────────────────┘
                 │ (Answers strictly based on retrieved Kazakhstan legal norms)
                 ▼
      [ Citation Extractor & Linker ]
                 │
                 ▼
      [ JSON Response with Verified Citations ]
      {
        "answer": "Согласно статье 56 ТК РК...",
        "citations": [
          {"document": "Трудовой кодекс РК", "article": "56", "url": "https://adilet.zan.kz/..."}
        ]
      }
===================================================================================================
```

---

## 🧰 Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16`)
- **ORM & Migrations:** SQLAlchemy 2.0 (Async), asyncpg, Alembic
- **LLM Provider:** Google Gemini 2.5 Flash (`google-genai` SDK) with Function Calling
- **Embeddings:** FastEmbed (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions)
- **HTML Parsing:** BeautifulSoup4, lxml
- **Containerization:** Docker Compose
- **Testing:** pytest, pytest-asyncio, httpx

---

## 📂 Project Structure

```text
adilet-ai/
├── docker-compose.yml              # PostgreSQL 16 + pgvector service (Port 5433)
├── requirements.txt                # Production dependencies
├── .env.example / .env             # Environment configuration
├── pytest.ini                      # Test configuration
├── backend/
│   ├── main.py                     # FastAPI entry point & Lifespan management
│   ├── alembic/                    # Async database migration scripts
│   └── app/
│       ├── core/
│       │   ├── config.py           # Pydantic Settings & dynamic .env loader
│       │   └── database.py         # Async database engine & session dependency
│       ├── models/
│       │   ├── base.py             # Timestamp mixin
│       │   ├── document.py         # Normative Legal Act (НПА) model
│       │   └── chunk.py            # Article chunk model with Vector column & HNSW index
│       ├── schemas/
│       │   ├── search.py           # Search request/response DTOs
│       │   └── chat.py             # Chat request, response, and citation DTOs
│       ├── services/
│       │   ├── parser.py           # Legislative HTML parser & state machine
│       │   ├── embeddings.py       # FastEmbed ONNX embedding service
│       │   ├── loader.py           # Database ingestion & bulk vectorizer
│       │   ├── crawler.py          # Automated crawler for key Kazakhstan codes
│       │   ├── retrieval.py        # Vector similarity search over pgvector
│       │   ├── llm.py              # Gemini Agentic Tool Calling & citation extractor
│       │   └── rag.py              # End-to-end RAG workflow orchestrator
│       └── api/
│           └── v1/
│               ├── health.py       # GET /api/v1/health (DB & pgvector verification)
│               ├── search.py       # POST /api/v1/search (Vector retrieval endpoint)
│               ├── chat.py         # POST /api/v1/chat (Agentic RAG endpoint)
│               ├── ingest.py       # POST /api/v1/ingest (Dynamic law ingestion)
│               └── router.py       # API v1 aggregator
└── tests/                          # Integration and end-to-end test suite
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.12+
- Docker & Docker Compose

### 2. Clone and Configure Environment

```bash
git clone https://github.com/your-username/adilet-ai.git
cd adilet-ai
```

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your Google Gemini API Key:
```env
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### 3. Start PostgreSQL with pgvector

```bash
docker compose up -d
```

### 4. Create Virtual Environment & Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5. Ingest Kazakhstan Legislation

Run the automated ingestion script to download, parse, vectorize, and store foundational Kazakhstan codes (Labor Code, Administrative Offences Code, Criminal Code, Consumer Protection Law, etc.):

```bash
python -m backend.app.services.crawler
```

### 6. Run the FastAPI Server

```bash
uvicorn backend.main:app --reload --port 8000
```

Open interactive Swagger documentation in your browser:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 📡 API Reference

### 1. `POST /api/v1/chat` — Ask Legal AI Assistant (Agentic RAG)
Automatically detects the applicable code, retrieves grounded articles, and provides an answer with verified citations.

**Request Body:**
```json
{
  "question": "Какой штраф предусмотрен за превышение скорости на 25 км/ч в Казахстане?",
  "top_k": 5
}
```

**Response Body:**
```json
{
  "question": "Какой штраф предусмотрен за превышение скорости на 25 км/ч в Казахстане?",
  "answer": "Согласно части 2 статьи 592 Кодекса Республики Казахстан об административных правонарушениях (КоАП РК) [1], превышение установленной скорости движения транспортного средства на величину от двадцати до сорока километров в час влечет штраф в размере десяти месячных расчетных показателей (МРП).",
  "citations": [
    {
      "source_index": 1,
      "document_title": "Кодекс Республики Казахстан об административных правонарушениях (КоАП РК)",
      "code_name": "koap_rk",
      "article_number": "592",
      "article_title": "Превышение установленной скорости движения",
      "clause_number": null,
      "source_url": "https://adilet.zan.kz/rus/docs/K1400000235"
    }
  ],
  "sources": [ ... ]
}
```

---

### 2. `POST /api/v1/search` — Pure Semantic Vector Search
Returns top-K matching statutory articles ranked by cosine similarity score.

**Request Body:**
```json
{
  "query": "Порядок расторжения трудового договора работником",
  "top_k": 3,
  "code_name": "tk_rk"
}
```

---

### 3. `GET /api/v1/health` — System Health Check
Verifies runtime state, PostgreSQL connectivity, and `pgvector` extension status.

**Response:**
```json
{
  "service": "KZ Legal RAG",
  "status": "healthy",
  "database": "connected",
  "pgvector": "active (v0.8.0)"
}
```

---

## 🧪 Running Tests

Execute the automated test suite covering vector indexing, semantic search, and agentic RAG:

```bash
pytest
```

---

## ⚖️ Legal Disclaimer

This application is intended for informational and research purposes only. The responses generated by the system do not constitute formal legal advice. For binding legal interpretations, consult certified legal professionals or official publications on [ИС «Әділет»](https://adilet.zan.kz).

---

## 📄 License

MIT License. Developed for modern AI-assisted legal research in the Republic of Kazakhstan.
