# Asistente SaaS — IA multi-tenant para Gmail

Asistente que lee, clasifica y responde los correos de una empresa con ayuda de IA. Cuando llega una notificación, analiza el mensaje, busca contexto en la base de conocimiento, redacta una respuesta profesional y ejecuta acciones como agendar citas o registrar actividades en el CRM. Los casos delicados (reembolsos, quejas) quedan en espera para que una persona los apruebe desde el panel web.

Está pensado como SaaS multi-tenant, así que varias empresas pueden usar la misma instancia sin mezclar sus datos. Todo el stack se levanta con Docker Compose.

---

## Características

- **Clasificación automática** de correos en cuatro tipos: duda, cita, reembolso y queja.
- **Respuestas redactadas por IA** con contexto de la base de conocimiento (RAG con pgvector).
- **Acciones automáticas**: crear eventos en Google Calendar y registrar actividades en el CRM.
- **Aprobación humana**: los reembolsos y quejas quedan en espera hasta decidir si se envían.
- **Multi-tenencia**: cada empresa accede solo a sus propios datos y documentos.
- **Modo simulado** (`MOCK_GOOGLE`) para desarrollar y probar sin credenciales reales de Google.
- **Panel web en tiempo real** con Jinja2, Tailwind CSS y HTMX.

### Cómo funciona

```
Correo entrante
  → notificación por webhook (o simulación)
  → tarea en segundo plano con Celery
  → el agente clasifica el correo (duda, cita, reembolso, queja)
  → si es duda, busca en la base de conocimiento (RAG)
  → la IA redacta una respuesta profesional
  → si es cita, crea el evento en Google Calendar y lo registra en el CRM
  → duda o cita: se envía automáticamente
  → reembolso o queja: queda pendiente de aprobación humana
```

---

## Tecnologías

| Componente | Qué hace |
|------------|----------|
| **FastAPI** (Python 3.11) | Servidor web: panel de control y API REST. |
| **Celery + Redis** | Procesamiento asíncrono de correos. |
| **PostgreSQL + pgvector** | Base de datos principal y búsqueda semántica (RAG). |
| **LangGraph** | Flujo de trabajo del agente: clasificar, enriquecer, redactar, ejecutar. |
| **Gemini (Google AI)** | Clasificación y redacción de respuestas. |
| **Google APIs (Gmail, Calendar)** | Integración real para leer, enviar correos y crear eventos. |
| **LlamaIndex + BGE embeddings** | Búsqueda semántica local sobre la base de conocimiento. |
| **Jinja2 + Tailwind CSS + HTMX** | Panel web liviano y dinámico. |
| **Docker Compose** | Orquestación de todos los servicios. |

---

## Estructura del proyecto

```
asistente-saas/
├── app/
│   ├── main.py              # Punto de entrada de FastAPI
│   ├── config.py            # Configuración desde variables de entorno
│   ├── api/v1/              # Endpoints REST (OAuth, webhooks, knowledge, mock)
│   ├── core/
│   │   ├── agents/          # Grafo cognitivo con LangGraph
│   │   ├── rag/             # Motor de búsqueda semántica
│   │   └── tools/           # Gmail, Calendar, CRM (reales y simulados)
│   ├── db/                  # Modelos SQLAlchemy y cifrado de tokens
│   ├── schemas/             # Modelos Pydantic
│   ├── static/              # Archivos estáticos
│   ├── templates/           # Plantillas Jinja2
│   ├── views/               # Rutas del panel web
│   └── workers/             # Tareas de Celery
├── docker-compose.yml       # Orquestación
├── Dockerfile
├── requirements.txt         # Dependencias Python
└── .env.example             # Plantilla de configuración
```

---

## Puesta en marcha

### Requisitos

- **Docker** y **Docker Compose** instalados.
- Una **API key de Google Gemini** (gratuita con límites).
- (Opcional) **Credenciales de OAuth2 de Google Cloud** si se quiere usar Gmail y Calendar reales.

### 1. Clona el repositorio y configura el entorno

```bash
git clone https://github.com/RmedranoCh/Asistente-SaaS---AI-Multi-Tenant
cd asistente-saas
cp .env.example .env
```

Edita `.env` con tus claves. Para desarrollo local, deja `MOCK_GOOGLE=true`: el sistema usa bases de datos locales que simulan Gmail, Calendar y CRM, así que no necesitas credenciales reales de Google.

Para generar `ENCRYPTION_KEY`:

```bash
python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

### 2. Levanta todo con un solo comando

```bash
docker compose up -d --build
```

Esto inicia cuatro servicios:

- **postgres_db**: PostgreSQL con pgvector.
- **redis_broker**: cola de mensajes para Celery.
- **web_api**: servidor FastAPI (con recarga automática).
- **celery_worker**: procesador de tareas en segundo plano.

### 3. Siembra datos de prueba

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed
```

Crea una empresa demo y 4 correos de ejemplo: una duda, una solicitud de reembolso, una petición de cita y una queja.

### 4. Abre el panel

| URL | Qué es |
|-----|--------|
| http://localhost:8000 | Panel de control |
| http://localhost:8000/docs | Documentación interactiva de la API |

---

## API REST

Todas las rutas comienzan con `/api/v1`.

### Datos de prueba

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/mock/seed` | Crea datos de prueba (empresa + correos) |
| POST | `/mock/reset` | Limpia los datos mock |
| GET | `/mock/inbox` | Correos entrantes simulados |
| GET | `/mock/sent` | Respuestas enviadas simuladas |
| GET | `/mock/events` | Eventos de calendario simulados |
| GET | `/mock/crm` | Actividades CRM simuladas |

### Webhooks y conocimiento

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/webhooks/gmail?token=...` | Webhook de Google Pub/Sub (o simulación) |
| POST | `/settings/knowledge/upload` | Sube un documento a la base de conocimiento |

### Tareas de Celery

| Tarea | Descripción |
|-------|-------------|
| `process_incoming_email` | Procesa un correo completo con el grafo cognitivo |
| `send_approved_email` | Envía un correo aprobado manualmente |

---

## Base de conocimiento (RAG)

Se pueden subir documentos en formato TXT, MD o PDF (máximo 10 MB cada uno). El sistema extrae el texto, lo divide en fragmentos, genera vectores con el modelo local `BAAI/bge-small-en-v1.5` y los almacena en PostgreSQL con pgvector.

Cuando llega un correo clasificado como **duda**, el agente consulta esta base para redactar una respuesta precisa, usando solo los datos de la empresa a la que pertenece el correo (multi-tenencia).

---

## Seguridad

- **Cifrado de tokens**: los accesos a Google se cifran con Fernet (AES-256) antes de guardarse. La llave se configura con `ENCRYPTION_KEY`.
- **Multi-tenencia**: cada empresa solo ve y accede a sus propios datos; las consultas RAG filtran por `company_id`.
- **Validación de webhooks**: el webhook de Pub/Sub verifica un token secreto antes de procesar la notificación.

---

## Tests

El proyecto usa `pytest`. Los tests corren **sin Docker ni credenciales**: usan una base SQLite en memoria y simulan Gemini y los servicios de Google.

```bash
pip install -r requirements-dev.txt
pytest
```

Cubren dos niveles:

- **Unitarios**: cifrado de tokens, parseo de correos, validación de configuración y los nodos del grafo del agente con la IA simulada.
- **De integración**: endpoints de la API (mock/testing, webhook de Pub/Sub y subida de conocimientos) contra una base SQLite.

> En `.github/workflows/ci.yml` hay un pipeline que ejecuta `pytest` en cada push o pull request.

---

## Licencia

Proyecto de código abierto. Consulta el archivo de licencia en el repositorio para más detalles.

---

¿Lo prefieres en inglés? → [README.en.md](README.en.md)