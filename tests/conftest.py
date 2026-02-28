"""
Pytest fixtures for PassTheAux tests.

Integration tests require a running Postgres instance.
Set TEST_DATABASE_URL env var to point at a test DB, or use docker-compose.
"""
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app

# Import all models so Base.metadata is fully populated for create_all
import app.models.session  # noqa: F401
import app.models.track  # noqa: F401
import app.models.vote  # noqa: F401
import app.models.playback  # noqa: F401
import app.models.event  # noqa: F401

# Use a separate test DB URL (default to same host, different DB name)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://passtheaux:passtheaux@localhost:5432/passtheaux_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Drop and recreate all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Per-test DB session that rolls back all flushes at the end for isolation."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async test client with DB dependency overridden."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
