# Asistente SaaS - AI Multi-Tenant

Asistente inteligente multi-tenancy para automatización de correos electrónicos empresariales. Procesa correos entrantes usando IA (Gemini + RAG), clasifica intenciones (duda, cita, reembolso, queja), ejecuta acciones en Google Calendar/CRM y gestiona flujos de aprobación humana.

## Arquitectura

```
                    ┌──────────────┐
                    │  Google/Gmail │
                    └──────┬───────┘
                           │ Pub/Sub Webhook
                    ┌──────▼───────┐
                    │   FastAPI     │
                    │  (Web + API)  │
                    └──┬───────┬───┘
                  ┌─────▼─┐ ┌──▼──────┐
                  │ Celery │ │PostgreSQL│
                  │ Worker │ │+ pgvector│
                  └────┬───┘ └────┬────┘
                  ┌────▼───┐      │
                  │  Redis  │◄─────┘
                  └─────────┘
```

- **FastAPI** — Servidor web con vistas Jinja2 + API REST
- **Celery + Redis** — Procesamiento asíncrono de correos entrantes
- **PostgreSQL + pgvector** — Base de datos principal + búsqueda semántica RAG
- **LangGraph** — Grafo de agentes cognitivos para clasificación y drafting
- **Gemini API** — Modelo de lenguaje para inferencia y generación de respuestas
- **Google APIs** — Gmail (historial, lectura, envío) y Calendar (creación de eventos)

## Requisitos

- Docker + Docker Compose
- API key de Gemini (`GEMINI_API_KEY`)
- (Opcional) Credenciales de OAuth2 de Google Cloud para integración real

## Inicio rápido

### 1. Clonar y configurar

```bash
git clone <repo-url>
cd asistente-saas
cp .env.example .env
```

Editar `.env` con tus claves:

```env
DATABASE_URL=postgresql://saas_admin:super_secret_password_2026@postgres_db:5432/asistente_saas_db
REDIS_URL=redis://redis_broker:6379/0
ENCRYPTION_KEY=<generar con: python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())">
JWT_SECRET_KEY=<string aleatorio>
GOOGLE_CLIENT_ID=mock_client_id
GOOGLE_CLIENT_SECRET=mock_client_secret
GOOGLE_PUBSUB_VERIFICATION_TOKEN=token_secreto_pubsub_xyz
GEMINI_API_KEY=<tu-api-key-de-gemini>
MOCK_GOOGLE=true
```

> `MOCK_GOOGLE=true` usa simulaciones en base de datos en lugar de APIs reales de Google. Ideal para desarrollo y pruebas.

### 2. Levantar servicios

```bash
docker compose up -d --build
```

### 3. Sembrar datos de prueba

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed
```

Esto crea:
- Una compañía demo con credenciales mock
- 4 correos de prueba: duda, reembolso, cita y queja

### 4. Ver estado

```bash
open http://localhost:8000
open http://localhost:8000/docs
```

## Endpoints principales

### API REST (`/api/v1`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/mock/seed` | Sembrar datos de prueba |
| POST | `/mock/reset` | Limpiar datos mock |
| GET | `/mock/inbox` | Ver correos entrantes mock |
| GET | `/mock/sent` | Ver respuestas enviadas mock |
| GET | `/mock/events` | Ver eventos de calendario mock |
| GET | `/mock/crm` | Ver actividades CRM mock |
| POST | `/webhooks/gmail?token=...` | Webhook Pub/Sub (simulado) |
| POST | `/settings/knowledge/upload` | Subir documento para RAG |

### Workers Celery

| Tarea | Descripción |
|-------|-------------|
| `process_incoming_email` | Procesa un correo con el grafo cognitivo |
| `send_approved_email` | Envía un correo aprobado por humano |

## Modo mock vs real

| Variable | `MOCK_GOOGLE=true` | `MOCK_GOOGLE=false` |
|----------|-------------------|-------------------|
| Gmail | SQL (`mock_inbox_emails`) | API de Google real |
| Calendar | SQL (`mock_calendar_events`) | API de Google real |
| CRM | SQL (`mock_crm_activities`) | API externa configurable |

## Flujo de procesamiento

```
Correo entrante
  → Webhook Pub/Sub → Celery task
    → Classify (Gemini: duda/cita/reembolso/queja)
      → RAG enrich (si es duda, busca en base vectorial)
        → Decision & Draft (Gemini genera respuesta)
          → Execute actions (Calendar, CRM si aplica)
            → Auto-send o Pending approval
```

## Tecnologías

- **Backend**: Python 3.11, FastAPI, SQLAlchemy async, Celery
- **IA**: Google Gemini, LangGraph, LlamaIndex + pgvector
- **Infra**: Docker Compose, PostgreSQL + pgvector, Redis
- **Frontend**: Jinja2, Tailwind CSS, HTMX
