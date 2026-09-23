import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 - Register all models on Base.metadata

# Alembic Config object
config = context.config

# Interpret config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Prepare cleaned database URL (convert asyncpg to sync for alembic CLI)
raw_db_url = settings.DATABASE_URL
if "+asyncpg" in raw_db_url:
    raw_db_url = raw_db_url.replace("+asyncpg", "")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

# Escape '%' for ConfigParser if set as option
config.set_main_option("sqlalchemy.url", raw_db_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=raw_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    if "[YOUR-PASSWORD]" in (raw_db_url or ""):
        print(
            "INFO: Placeholder '[YOUR-PASSWORD]' detected in DATABASE_URL; "
            "using in-memory engine for local schema reflection."
        )
        connectable = create_engine("sqlite:///:memory:")
    else:
        connectable = create_engine(
            raw_db_url,
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
