# Asistente SaaS — AI multi-tenant for Gmail

An assistant that reads, classifies, and replies to a company's emails with AI. When a notification arrives, it analyzes the message, looks for context in the knowledge base, drafts a professional reply, and runs actions such as scheduling appointments or logging CRM activities. Sensitive cases (refunds, complaints) stay on hold until a person approves them from the web dashboard.

It's designed as a multi-tenant SaaS, so multiple companies can use the same instance without mixing their data. The whole stack runs on Docker Compose.

---

## Features

- **Automatic classification** of emails into four types: question, appointment, refund, and complaint.
- **AI-drafted replies** backed by the knowledge base (RAG with pgvector).
- **Automatic actions**: create Google Calendar events and log CRM activities.
- **Human approval**: refunds and complaints stay on hold until you decide whether to send them.
- **Multi-tenancy**: each company only accesses its own data and documents.
- **Simulated mode** (`MOCK_GOOGLE`) to develop and test without real Google credentials.
- **Real-time web dashboard** built with Jinja2, Tailwind CSS, and HTMX.

### How it works

```
Incoming email
  → webhook notification (or simulation)
  → background task with Celery
  → the agent classifies the email (question, appointment, refund, complaint)
  → if it's a question, it searches the knowledge base (RAG)
  → the AI drafts a professional reply
  → if it's an appointment, it creates the Google Calendar event and logs it in the CRM
  → question or appointment: sent automatically
  → refund or complaint: held for human approval
```

---

## Tech stack

| Component | What it does |
|------------|------------|
| **FastAPI** (Python 3.11) | Web server: dashboard and REST API. |
| **Celery + Redis** | Asynchronous email processing. |
| **PostgreSQL + pgvector** | Main database and semantic search (RAG). |
| **LangGraph** | Agent workflow: classify, enrich, draft, execute. |
| **Gemini (Google AI)** | Classification and reply drafting. |
| **Google APIs (Gmail, Calendar)** | Real integration for reading, sending emails, and creating events. |
| **LlamaIndex + BGE embeddings** | Local semantic search over the knowledge base. |
| **Jinja2 + Tailwind CSS + HTMX** | Lightweight, dynamic web dashboard. |
| **Docker Compose** | Orchestration of all services. |

---

## Project structure

```
asistente-saas/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration from environment variables
│   ├── api/v1/              # REST endpoints (OAuth, webhooks, knowledge, mock)
│   ├── core/
│   │   ├── agents/          # LangGraph cognitive graph
│   │   ├── rag/             # Semantic search engine
│   │   └── tools/           # Gmail, Calendar, CRM (real and mocked)
│   ├── db/                  # SQLAlchemy models and token encryption
│   ├── schemas/             # Pydantic models
│   ├── static/              # Static files
│   ├── templates/           # Jinja2 templates
│   ├── views/               # Web dashboard routes
│   └── workers/             # Celery tasks
├── docker-compose.yml       # Orchestration
├── Dockerfile
├── requirements.txt         # Python dependencies
└── .env.example             # Configuration template
```

---

## Getting started

### Requirements

- **Docker** and **Docker Compose** installed.
- A **Google Gemini API key** (free with usage limits).
- (Optional) **Google Cloud OAuth2 credentials** if you want to use real Gmail and Calendar.

### 1. Clone the repository and configure the environment

```bash
git clone https://github.com/RmedranoCh/Asistente-SaaS---AI-Multi-Tenant
cd asistente-saas
cp .env.example .env
```

Edit `.env` with your keys. For local development, leave `MOCK_GOOGLE=true`: the system uses local databases that simulate Gmail, Calendar, and CRM, so no real Google credentials are needed.

To generate `ENCRYPTION_KEY`:

```bash
python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

### 2. Start everything with a single command

```bash
docker compose up -d --build
```

This launches four services:

- **postgres_db**: PostgreSQL with pgvector.
- **redis_broker**: message queue for Celery.
- **web_api**: FastAPI server (with hot reload).
- **celery_worker**: background task processor.

### 3. Seed test data

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed
```

It creates a demo company and 4 sample emails: a question, a refund request, an appointment request, and a complaint.

### 4. Open the dashboard

| URL | What it is |
|-----|------------|
| http://localhost:8000 | Control panel |
| http://localhost:8000/docs | Interactive API documentation |

---

## REST API

All routes start with `/api/v1`.

### Test data

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/mock/seed` | Create test data (company + emails) |
| POST | `/mock/reset` | Clear mock data |
| GET | `/mock/inbox` | Simulated incoming emails |
| GET | `/mock/sent` | Simulated sent replies |
| GET | `/mock/events` | Simulated calendar events |
| GET | `/mock/crm` | Simulated CRM activities |

### Webhooks and knowledge

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/webhooks/gmail?token=...` | Google Pub/Sub webhook (or simulation) |
| POST | `/settings/knowledge/upload` | Upload a document to the knowledge base |

### Celery tasks

| Task | Description |
|-------|-------------|
| `process_incoming_email` | Process a full email through the cognitive graph |
| `send_approved_email` | Send a manually approved email |

---

## Knowledge base (RAG)

You can upload documents in TXT, MD, or PDF format (max 10 MB each). The system extracts the text, splits it into chunks, generates vectors with the local `BAAI/bge-small-en-v1.5` model, and stores them in PostgreSQL with pgvector.

When an email classified as a **question** arrives, the agent queries this base to draft an accurate reply, using only the data of the company the email belongs to (multi-tenancy).

---

## Security

- **Token encryption**: Google access tokens are encrypted with Fernet (AES-256) before storage. The key is set with `ENCRYPTION_KEY`.
- **Multi-tenancy**: each company only sees and accesses its own data; RAG queries filter by `company_id`.
- **Webhook validation**: the Pub/Sub webhook verifies a secret token before processing the notification.

---

## Tests

The project uses `pytest`. The test suite runs **without Docker or credentials**: it uses an in-memory SQLite database and mocks Gemini and the Google services.

```bash
pip install -r requirements-dev.txt
pytest
```

Two levels are covered:

- **Unit tests**: token encryption, email parsing, config validation, and the agent graph nodes with mocked AI.
- **Integration tests**: REST endpoints (mock/testing data, Pub/Sub webhook, and knowledge upload) against a SQLite database.

> There's a pipeline in `.github/workflows/ci.yml` that runs `pytest` on every push or pull request.

---

## License

Open source project. Check the license file in the repository for details.

---

Prefer Spanish? → [README.md](README.md)