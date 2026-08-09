import os

os.environ.setdefault("MOCK_GOOGLE", "true")
os.environ.setdefault("GEMINI_API_KEY", "test-key-no-real-usage")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault(
    "GOOGLE_PUBSUB_VERIFICATION_TOKEN", "test_pubsub_verification_token"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-not-for-prod")
os.environ.setdefault(
    "ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdHMtMzI="
)
os.environ.setdefault(
    "DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db


@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> AsyncIterator[Callable[[], AsyncSession]]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False)

    def _get_session() -> AsyncSession:
        return maker()

    yield _get_session


@pytest_asyncio.fixture
async def client(
    db_engine: AsyncEngine,
    session_factory: Callable[[], AsyncSession],
) -> AsyncIterator[AsyncClient]:
    from app.main import app

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        session = session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _reset_ai_client():
    """Restablece el cliente de Gemini entre pruebas para evitar estado compartido."""
    from app.core.agents import nodes

    nodes._ai_client = None