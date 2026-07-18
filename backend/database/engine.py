"""Async SQLAlchemy engine and session factory.

Supports both PostgreSQL (production) and SQLite (local dev fallback).
Set DATABASE_URL env var to switch:
  - Postgres: postgresql+asyncpg://user:pass@host/dbname
  - SQLite:   sqlite+aiosqlite:///./backend/storage/app.db  (default)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Prefer PostgreSQL; fall back to async SQLite for local dev without Postgres
_raw_url = os.getenv("DATABASE_URL", "")

if not _raw_url:
    # Local dev: use SQLite via aiosqlite.
    # Anchor the default path to the backend/ dir so it doesn't depend on cwd.
    import pathlib
    _backend_dir = pathlib.Path(__file__).resolve().parents[1]
    _storage = pathlib.Path(os.getenv("STORAGE_DIR", _backend_dir / "storage"))
    _storage.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{_storage}/app.db"
else:
    # Replace postgres:// with postgresql+asyncpg:// for SQLAlchemy async
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1).replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
