import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.config import settings
from app.api.v1.api import api_router
from app.views.router import views_router
from app.db.session import engine
from app.db.models import Base

logger = logging.getLogger(__name__)


async def _init_database_schema() -> None:
    try:
        async with engine.begin() as conn:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as ext_err:
                logger.warning(
                    "No se pudo habilitar la extensión pgvector automáticamente: %s",
                    ext_err,
                )
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error("Error inicializando el esquema de base de datos: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _init_database_schema()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": "Ha ocurrido un error inesperado en el servidor. Nuestro equipo técnico ha sido notificado.",
        },
    )


app.include_router(views_router)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
