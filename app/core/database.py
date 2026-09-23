from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# High-concurrency async engine configured for Supabase Transaction Pooler (port 6543)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=False,
    connect_args={"statement_cache_size": 0},
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass
