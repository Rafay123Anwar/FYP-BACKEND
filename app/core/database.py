from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# High-concurrency async engine configured for Supabase Transaction Pooler (port 6543)
# pool_size=20 + max_overflow=30 supports 50 simultaneous DB connections —
# sufficient headroom for 100 concurrent users (auth queries are <5ms each).
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=300,          # recycle connections every 5 min
    pool_pre_ping=True,        # detect stale connections before use
    pool_timeout=10,           # fail fast if pool exhausted (don't hang 30s)
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
