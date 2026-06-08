import logging
from celery import Celery
from sqlalchemy import text

from app.config import settings
from app.db.session import engine
from app.db.models import Base

logger = logging.getLogger(__name__)

celery_app = Celery(
    "asistente_saas_workers",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


def _bootstrap_database() -> None:
    """Asegura la extensión pgvector y las tablas antes de procesar tareas."""
    import asyncio

    async def _setup():
        try:
            async with engine.begin() as conn:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                except Exception as ext_err:
                    logger.warning("No se pudo habilitar pgvector: %s", ext_err)
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            logger.error("Bootstrap de DB en worker falló: %s", e)
        finally:
            await engine.dispose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        loop.create_task(_setup())
    else:
        asyncio.run(_setup())


_bootstrap_database()

import app.workers.tasks  # noqa: E402,F401  (registro de tareas)
