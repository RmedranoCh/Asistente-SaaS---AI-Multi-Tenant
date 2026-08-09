# Asistente SaaS — IA Multi-Tenant para Gmail

**Un asistente inteligente que lee, clasifica y responde correos electrónicos empresariales automáticamente, con supervisión humana cuando hace falta.**

Imagina que tu bandeja de entrada recibe decenas de correos al día: dudas de clientes, solicitudes de reembolso, quejas, peticiones de citas... Este sistema se encarga de todo el proceso: recibe la notificación, analiza el correo con inteligencia artificial, busca información relevante en tu base de conocimiento, redacta una respuesta profesional, programa eventos en el calendario si es necesario, registra actividades en el CRM, y —dependiendo del tipo de correo— lo envía automáticamente o lo pone en espera para que tú lo apruebes.

---

## Cómo funciona

```
Correo entrante
  → Llega una notificación vía webhook (o simulación)
  → Se dispara una tarea en segundo plano con Celery
    → El agente de IA clasifica el correo (duda, cita, reembolso, queja)
      → Si es una duda, busca en la base de conocimiento interna (RAG)
        → La IA genera una respuesta profesional
          → Si es una cita, crea el evento en Google Calendar y lo registra en el CRM
            → Si es duda o cita → se envía automáticamente
            → Si es reembolso o queja → queda pendiente de aprobación humana
```

Todo esto ocurre en segundos. Desde el panel web puedes ver el estado de cada correo, aprobar o rechazar respuestas, y monitorear todo en tiempo real.

---

## Tecnologías que usa

| Componente | ¿Qué hace? |
|------------|------------|
| **FastAPI** (Python 3.11) | El servidor web. Sirve el panel de control y la API REST. |
| **Celery + Redis** | Procesa los correos de forma asíncrona para no bloquear nada. |
| **PostgreSQL + pgvector** | Base de datos principal. pgvector permite buscar por similitud semántica (RAG). |
| **LangGraph** | Define el flujo de trabajo del agente de IA: clasificar, enriquecer, redactar, ejecutar acciones. |
| **Gemini (Google AI)** | El cerebro. Clasifica correos, extrae información y redacta respuestas. |
| **Google APIs (Gmail, Calendar)** | Integración real para leer, enviar correos y crear eventos. |
| **LlamaIndex + BGE embeddings** | Motor de búsqueda semántica local para responder preguntas desde tu base de conocimiento. |
| **Jinja2 + Tailwind CSS + HTMX** | Panel web moderno, dinámico y liviano, sin frameworks JS pesados. |
| **Docker Compose** | Todo se levanta con un solo comando. |

---

## Estructura del proyecto

```
asistente-saas/
├── app/
│   ├── main.py              # Punto de entrada de FastAPI
│   ├── config.py            # Configuración desde variables de entorno
│   ├── api/                 # Endpoints REST
│   │   └── v1/
│   │       ├── google_oauth.py   # Conexión con Google OAuth2
│   │       ├── webhooks.py       # Webhook de Google Pub/Sub
│   │       ├── knowledge.py      # Subida de documentos para RAG
│   │       └── mock_test.py      # Endpoints de datos de prueba
│   ├── core/                # Lógica de negocio
│   │   ├── agents/               # Grafo cognitivo con LangGraph
│   │   │   ├── graph.py          # Definición del flujo de trabajo
│   │   │   ├── nodes.py          # Cada paso del agente
│   │   │   └── states.py         # Estado del agente
│   │   ├── rag/                  # Motor de búsqueda semántica
│   │   │   ├── embeddings.py     # Embeddings con BGE local
│   │   │   └── engine.py         # RAG multi-tenencia con pgvector
│   │   └── tools/                # Integraciones externas
│   │       ├── gmail_actions.py  # Gmail real
│   │       ├── calendar.py       # Google Calendar real
│   │       ├── crm.py            # API de CRM externa
│   │       ├── mock_gmail.py     # Simulación de Gmail
│   │       ├── mock_calendar.py  # Simulación de Calendar
│   │       └── mock_crm.py       # Simulación de CRM
│   ├── db/                  # Capa de datos
│   │   ├── models.py        # Modelos SQLAlchemy
│   │   ├── session.py       # Conexión a base de datos
│   │   └── security.py      # Cifrado de tokens OAuth
│   ├── schemas/             # Modelos Pydantic
│   ├── static/              # Archivos estáticos (CSS, JS)
│   ├── templates/           # Plantillas Jinja2
│   │   ├── base.html, dashboard.html, login.html, settings.html
│   │   └── components/      # Fragmentos HTMX
│   ├── views/               # Rutas del panel web
│   │   ├── web_auth.py, web_dashboard.py, web_settings.py
│   └── workers/             # Tareas asíncronas Celery
│       ├── worker.py
│       └── tasks.py
├── docker-compose.yml       # Orquestación de servicios
├── Dockerfile               # Construcción del contenedor
├── requirements.txt         # Dependencias Python
├── tailwind.config.js
└── .env.example             # Plantilla de configuración
```

---

## Requisitos

- **Docker** y **Docker Compose** instalados
- Una **API key de Google Gemini** (gratuita con límites)
- (Opcional) **Credenciales de OAuth2 de Google Cloud** si quieres usar Gmail y Calendar reales

---

## Inicio rápido

### 1. Clona el proyecto

```bash
git clone https://github.com/RmedranoCh/Asistente-SaaS---AI-Multi-Tenant
cd asistente-saas
cp .env.example .env
```

### 2. Configura las variables de entorno

Edita el archivo `.env` con tus claves:

```env
DATABASE_URL=postgresql://saas_admin:super_secret_password_2026@postgres_db:5432/asistente_saas_db
REDIS_URL=redis://redis_broker:6379/0
ENCRYPTION_KEY=<generar con: python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())">
JWT_SECRET_KEY=<un string aleatorio seguro>
GOOGLE_CLIENT_ID=mock_client_id
GOOGLE_CLIENT_SECRET=mock_client_secret
GOOGLE_PUBSUB_VERIFICATION_TOKEN=token_secreto_pubsub_xyz
GEMINI_API_KEY=<tu-api-key-de-gemini>
MOCK_GOOGLE=true
```

> **Tips:**
> - `ENCRYPTION_KEY` debe ser una cadena de 32 bytes codificada en Base64 segura para URL. Puedes generarla con `python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`.
> - `MOCK_GOOGLE=true` hace que el sistema use bases de datos locales para simular Gmail, Calendar y CRM. Es ideal para desarrollo y pruebas sin necesidad de credenciales reales de Google.

### 3. Levanta todo con un solo comando

```bash
docker compose up -d --build
```

Esto inicia cuatro servicios:
- **postgres_db**: Base de datos PostgreSQL con pgvector
- **redis_broker**: Cola de mensajes para Celery
- **web_api**: Servidor web FastAPI (con recarga automática de código)
- **celery_worker**: Procesador de tareas en segundo plano

### 4. Siembra datos de prueba

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed
```

Esto crea:
- Una empresa demo con credenciales simuladas
- 4 correos de ejemplo: una duda, una solicitud de reembolso, una petición de cita y una queja

### 5. Abre el panel

```bash
http://localhost:8000          # Panel de control
http://localhost:8000/docs     # Documentación interactiva de la API
```

---

## Endpoints de la API REST

Todas las rutas comienzan con `/api/v1`.

### Datos de prueba (Mock)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/mock/seed` | Crea datos de prueba (empresa + correos) |
| POST | `/mock/reset` | Limpia todos los datos mock |
| GET | `/mock/inbox` | Ver correos entrantes simulados |
| GET | `/mock/sent` | Ver respuestas enviadas simuladas |
| GET | `/mock/events` | Ver eventos de calendario simulados |
| GET | `/mock/crm` | Ver actividades CRM simuladas |

### Webhooks y conocimiento

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/webhooks/gmail?token=...` | Webhook de Google Pub/Sub (o simulación) |
| POST | `/settings/knowledge/upload` | Subir un documento para la base de conocimiento |

### Tareas de Celery

| Tarea | Descripción |
|-------|-------------|
| `process_incoming_email` | Procesa un correo completo con el grafo cognitivo |
| `send_approved_email` | Envía un correo que fue aprobado manualmente |

---

## Modo simulado vs. real

El sistema tiene un interruptor mágico: la variable `MOCK_GOOGLE`. Con ella puedes alternar entre datos simulados en base de datos y las APIs reales de Google.

| Componente | `MOCK_GOOGLE=true` | `MOCK_GOOGLE=false` |
|------------|-------------------|-------------------|
| **Gmail** | Tabla `mock_inbox_emails` en PostgreSQL | API real de Gmail (leer, enviar, historial) |
| **Calendar** | Tabla `mock_calendar_events` en PostgreSQL | API real de Google Calendar |
| **CRM** | Tabla `mock_crm_activities` en PostgreSQL | API externa configurable vía HTTP |

**Para desarrollo local:** deja `MOCK_GOOGLE=true`. No necesitas credenciales de Google de ningún tipo.

**Para producción:** cambia a `MOCK_GOOGLE=false`, completa las credenciales de OAuth2 y configura el webhook de Pub/Sub en Google Cloud Console.

---

## Panel web

El dashboard está construido con Jinja2, Tailwind CSS y HTMX. Es liviano, responsivo y se actualiza solo.

- **Dashboard** (`/dashboard`): Muestra estadísticas en tiempo real (correos pendientes, enviados, totales) y la lista de correos procesados. Se actualiza cada 5 segundos sin recargar la página.
- **Aprobaciones**: Los correos marcados para aprobación humana (reembolsos, quejas) aparecen con botones para **aprobar** o **rechazar**.
- **Configuración** (`/settings`): Permite conectar una cuenta de Google, ver documentos subidos y subir nuevos archivos a la base de conocimiento.

---

## Base de conocimiento (RAG)

Puedes subir documentos en formato TXT, MD o PDF (máximo 10 MB cada uno). El sistema:
1. Extrae el texto del documento
2. Lo divide en fragmentos
3. Genera vectores de embedding usando el modelo local `BAAI/bge-small-en-v1.5`
4. Almacena los vectores en PostgreSQL con pgvector

Cuando llega un correo clasificado como **duda**, el agente consulta esta base de conocimiento para encontrar información relevante y redactar una respuesta precisa, usando solo los datos de la empresa a la que pertenece el correo (multi-tenencia).

---

## Modelo de datos

El sistema maneja estas entidades principales:

| Tabla | ¿Qué guarda? |
|-------|-------------|
| `Company` | Empresas inquilinas (multi-tenencia) |
| `GoogleCredential` | Tokens de OAuth2 cifrados por empresa |
| `KnowledgeDocument` | Metadatos de documentos subidos |
| `EmailLog` | Bitácora de correos procesados, con estado y respuesta |
| `MockInboxEmail` | Correos entrantes simulados |
| `MockSentEmail` | Respuestas enviadas simuladas |
| `MockCalendarEvent` | Eventos de calendario simulados |
| `MockCrmActivity` | Actividades CRM simuladas |

---

## Flujo de procesamiento detallado

1. **Llega un correo** — Ya sea por webhook real de Google Pub/Sub o porque se sembraron datos mock.
2. **Se encola una tarea** — Celery recibe el mensaje y ejecuta `process_incoming_email`.
3. **El agente clasifica** — Gemini determina si es: duda, cita, reembolso o queja.
4. **Si es duda** — Se consulta la base vectorial (RAG) para obtener contexto relevante.
5. **Se redacta una respuesta** — Gemini genera un borrador profesional en español.
6. **Se ejecutan acciones** — Si es una cita, se crea un evento en Calendar y se registra en CRM.
7. **Se decide el destino**:
   - *Duda* o *Cita* → se envía automáticamente.
   - *Reembolso* o *Queja* → queda en estado `PENDING_APPROVAL`.
   - Si algo falla → también queda pendiente de revisión humana.
8. **Un humano revisa** — Desde el dashboard se puede aprobar (se envía) o rechazar.
9. **Fin** — El correo queda registrado con su estado final.

---

## Seguridad

- **Cifrado de tokens**: Los tokens de acceso a Google se cifran con Fernet (AES-256) antes de guardarse en la base de datos. La llave de cifrado se configura vía `ENCRYPTION_KEY`.
- **Multi-tenencia**: Cada empresa solo ve y accede a sus propios datos. Las consultas RAG filtran por `company_id`.
- **Validación de webhooks**: El webhook de Pub/Sub verifica un token secreto antes de procesar la notificación.

---

## Tests

El proyecto usa `pytest`. Los tests están pensados para correr **sin Docker ni credenciales**: usan una base de datos SQLite en memoria y simulan Gemini y los servicios de Google, así que puedes ejecutarlos en tu máquina de forma directa.

```bash
pip install -r requirements-dev.txt
pytest
```

Se cubren dos niveles:

- **Unitarios**: cifrado de tokens, parseo de correos de Gmail, validación de la configuración y los nodos del grafo del agente (clasificar, buscar en RAG, redactar y ejecutar acciones) con la IA simulada.
- **De integración**: los endpoints de la API (mock/testing, webhook de Pub/Sub y subida de conocimientos) contra una base SQLite.

> En `.github/workflows/ci.yml` hay un pipeline que instala lo necesario y ejecuta `pytest` en cada push o pull request.

---

## Licencia

Proyecto de código abierto. Consulta el archivo de licencia en el repositorio para más detalles.

---

---

# Asistente SaaS — AI Multi-Tenant for Gmail

**An intelligent assistant that reads, classifies, and replies to business emails automatically, with human oversight when needed.**

Imagine your inbox receiving dozens of emails every day: customer questions, refund requests, complaints, meeting requests... This system handles the entire process: it receives the notification, analyzes the email with artificial intelligence, searches relevant information in your knowledge base, drafts a professional reply, schedules calendar events if needed, logs CRM activities, and — depending on the email type — sends it automatically or holds it for your approval.

---

## How it works

```
Incoming email
  → A webhook notification arrives (or simulation)
  → A background task is triggered via Celery
    → The AI agent classifies the email (question, appointment, refund, complaint)
      → If it's a question, it searches the internal knowledge base (RAG)
        → The AI generates a professional reply
          → If it's an appointment, it creates a Google Calendar event and logs it in the CRM
            → Question or appointment → sent automatically
            → Refund or complaint → held for human approval
```

All of this happens in seconds. From the web dashboard you can see the status of each email, approve or reject replies, and monitor everything in real time.

---

## Tech stack

| Component | What it does |
|------------|------------|
| **FastAPI** (Python 3.11) | Web server. Serves the dashboard and REST API. |
| **Celery + Redis** | Processes emails asynchronously without blocking anything. |
| **PostgreSQL + pgvector** | Main database. pgvector enables semantic similarity search (RAG). |
| **LangGraph** | Defines the AI agent workflow: classify, enrich, draft, execute actions. |
| **Gemini (Google AI)** | The brain. Classifies emails, extracts information, and drafts replies. |
| **Google APIs (Gmail, Calendar)** | Real integration to read, send emails, and create events. |
| **LlamaIndex + BGE embeddings** | Local semantic search engine to answer questions from your knowledge base. |
| **Jinja2 + Tailwind CSS + HTMX** | Modern, dynamic, lightweight web dashboard without heavy JS frameworks. |
| **Docker Compose** | Everything spins up with a single command. |

---

## Project structure

```
asistente-saas/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment variable configuration
│   ├── api/                 # REST endpoints
│   │   └── v1/
│   │       ├── google_oauth.py   # Google OAuth2 connection
│   │       ├── webhooks.py       # Google Pub/Sub webhook
│   │       ├── knowledge.py      # Document upload for RAG
│   │       └── mock_test.py      # Test data endpoints
│   ├── core/                # Business logic
│   │   ├── agents/               # LangGraph cognitive graph
│   │   │   ├── graph.py          # Workflow definition
│   │   │   ├── nodes.py          # Each agent step
│   │   │   └── states.py         # Agent state
│   │   ├── rag/                  # Semantic search engine
│   │   │   ├── embeddings.py     # Local BGE embeddings
│   │   │   └── engine.py         # Multi-tenant RAG with pgvector
│   │   └── tools/                # External integrations
│   │       ├── gmail_actions.py  # Real Gmail
│   │       ├── calendar.py       # Real Google Calendar
│   │       ├── crm.py            # External CRM API
│   │       ├── mock_gmail.py     # Gmail simulation
│   │       ├── mock_calendar.py  # Calendar simulation
│   │       └── mock_crm.py       # CRM simulation
│   ├── db/                  # Data layer
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── session.py       # Database connection
│   │   └── security.py      # OAuth token encryption
│   ├── schemas/             # Pydantic models
│   ├── static/              # Static files (CSS, JS)
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html, dashboard.html, login.html, settings.html
│   │   └── components/      # HTMX fragments
│   ├── views/               # Web dashboard routes
│   │   ├── web_auth.py, web_dashboard.py, web_settings.py
│   └── workers/             # Celery async tasks
│       ├── worker.py
│       └── tasks.py
├── docker-compose.yml       # Service orchestration
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
├── tailwind.config.js
└── .env.example             # Configuration template
```

---

## Requirements

- **Docker** and **Docker Compose** installed
- A **Google Gemini API key** (free with usage limits)
- (Optional) **Google Cloud OAuth2 credentials** if you want to use real Gmail and Calendar

---

## Quick start

### 1. Clone the project

```bash
git clone https://github.com/RmedranoCh/Asistente-SaaS---AI-Multi-Tenant
cd asistente-saas
cp .env.example .env
```

### 2. Configure environment variables

Edit the `.env` file with your keys:

```env
DATABASE_URL=postgresql://saas_admin:super_secret_password_2026@postgres_db:5432/asistente_saas_db
REDIS_URL=redis://redis_broker:6379/0
ENCRYPTION_KEY=<generate with: python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())">
JWT_SECRET_KEY=<a secure random string>
GOOGLE_CLIENT_ID=mock_client_id
GOOGLE_CLIENT_SECRET=mock_client_secret
GOOGLE_PUBSUB_VERIFICATION_TOKEN=token_secreto_pubsub_xyz
GEMINI_API_KEY=<your-gemini-api-key>
MOCK_GOOGLE=true
```

> **Tips:**
> - `ENCRYPTION_KEY` must be a 32-byte URL-safe Base64 encoded string. Generate one with `python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`.
> - `MOCK_GOOGLE=true` makes the system use local databases to simulate Gmail, Calendar, and CRM. Ideal for development and testing without real Google credentials.

### 3. Start everything with a single command

```bash
docker compose up -d --build
```

This launches four services:
- **postgres_db**: PostgreSQL database with pgvector
- **redis_broker**: Message queue for Celery
- **web_api**: FastAPI web server (with hot reload)
- **celery_worker**: Background task processor

### 4. Seed test data

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed
```

This creates:
- A demo company with mock credentials
- 4 sample emails: a question, a refund request, an appointment request, and a complaint

### 5. Open the dashboard

```bash
http://localhost:8000          # Control panel
http://localhost:8000/docs     # Interactive API documentation
```

---

## REST API endpoints

All routes start with `/api/v1`.

### Test data (Mock)

| Method | Route | Description |
|--------|------|-------------|
| POST | `/mock/seed` | Create test data (company + emails) |
| POST | `/mock/reset` | Clear all mock data |
| GET | `/mock/inbox` | View simulated incoming emails |
| GET | `/mock/sent` | View simulated sent replies |
| GET | `/mock/events` | View simulated calendar events |
| GET | `/mock/crm` | View simulated CRM activities |

### Webhooks & knowledge

| Method | Route | Description |
|--------|------|-------------|
| POST | `/webhooks/gmail?token=...` | Google Pub/Sub webhook (or simulation) |
| POST | `/settings/knowledge/upload` | Upload a document to the knowledge base |

### Celery tasks

| Task | Description |
|-------|-------------|
| `process_incoming_email` | Process a full email through the cognitive graph |
| `send_approved_email` | Send a manually approved email |

---

## Mock vs. real mode

The system has a magic switch: the `MOCK_GOOGLE` variable. Toggle between database simulations and real Google APIs.

| Component | `MOCK_GOOGLE=true` | `MOCK_GOOGLE=false` |
|------------|-------------------|-------------------|
| **Gmail** | `mock_inbox_emails` table in PostgreSQL | Real Gmail API (read, send, history) |
| **Calendar** | `mock_calendar_events` table in PostgreSQL | Real Google Calendar API |
| **CRM** | `mock_crm_activities` table in PostgreSQL | Configurable external HTTP API |

**For local development:** leave `MOCK_GOOGLE=true`. No Google credentials needed.

**For production:** set `MOCK_GOOGLE=false`, complete the OAuth2 credentials, and configure the Pub/Sub webhook in Google Cloud Console.

---

## Web dashboard

The dashboard is built with Jinja2, Tailwind CSS, and HTMX. It's lightweight, responsive, and self-updating.

- **Dashboard** (`/dashboard`): Shows real-time stats (pending, sent, total) and the list of processed emails. Auto-refreshes every 5 seconds without page reload.
- **Approvals**: Emails flagged for human approval (refunds, complaints) appear with **approve** or **reject** buttons.
- **Settings** (`/settings`): Connect a Google account, view uploaded documents, and upload new files to the knowledge base.

---

## Knowledge base (RAG)

You can upload documents in TXT, MD, or PDF format (max 10 MB each). The system:
1. Extracts text from the document
2. Splits it into chunks
3. Generates embedding vectors using the local `BAAI/bge-small-en-v1.5` model
4. Stores the vectors in PostgreSQL with pgvector

When an email classified as a **question** arrives, the agent queries this knowledge base to find relevant information and draft an accurate reply, using only the data belonging to that email's company (multi-tenancy).

---

## Data model

The system manages these main entities:

| Table | What it stores |
|-------|-------------|
| `Company` | Tenant companies (multi-tenancy) |
| `GoogleCredential` | Encrypted OAuth2 tokens per company |
| `KnowledgeDocument` | Uploaded document metadata |
| `EmailLog` | Processed email log with status and reply |
| `MockInboxEmail` | Simulated incoming emails |
| `MockSentEmail` | Simulated sent replies |
| `MockCalendarEvent` | Simulated calendar events |
| `MockCrmActivity` | Simulated CRM activities |

---

## Detailed processing flow

1. **An email arrives** — Either via a real Google Pub/Sub webhook or by seeding mock data.
2. **A task is queued** — Celery receives the message and runs `process_incoming_email`.
3. **The agent classifies** — Gemini determines if it's: a question, appointment, refund, or complaint.
4. **If it's a question** — The vector database (RAG) is queried for relevant context.
5. **A reply is drafted** — Gemini generates a professional draft in Spanish.
6. **Actions are executed** — If it's an appointment, a Calendar event is created and logged in CRM.
7. **The destination is decided**:
   - *Question* or *Appointment* → sent automatically.
   - *Refund* or *Complaint* → status becomes `PENDING_APPROVAL`.
   - If something fails → also held for human review.
8. **A human reviews** — From the dashboard, approve (which sends it) or reject.
9. **Done** — The email is recorded with its final status.

---

## Security

- **Token encryption**: Google access tokens are encrypted with Fernet (AES-256) before being stored in the database. The encryption key is configured via `ENCRYPTION_KEY`.
- **Multi-tenancy**: Each company can only see and access its own data. RAG queries filter by `company_id`.
- **Webhook validation**: The Pub/Sub webhook verifies a secret token before processing the notification.

---

## Tests

The project uses `pytest`. The test suite is designed to run **without Docker or any credentials**: it uses an in-memory SQLite database and fakes Gemini and the Google services, so you can run it directly on your machine.

```bash
pip install -r requirements-dev.txt
pytest
```

Two levels are covered:

- **Unit tests**: token encryption, Gmail message parsing, config validation, and the agent graph nodes (classify, RAG lookup, draft, and execute actions) with the AI mocked out.
- **Integration tests**: the REST API endpoints (mock/testing data, Pub/Sub webhook, and knowledge upload) against a SQLite database.

> There's a pipeline in `.github/workflows/ci.yml` that installs the dependencies and runs `pytest` on every push or pull request.

---

## License

Open source project. Check the license file in the repository for details.
