"""Alembic runtime using only the email-service settings and metadata."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.database.base import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
settings = get_settings()
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Keep email-service autogeneration scoped to its own model tables."""
    if type_ == "table":
        return name in target_metadata.tables
    return True


def _url() -> str:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured for email-service migrations")
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        version_table="email_service_alembic_version",
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
        version_table="email_service_alembic_version",
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        _run(supplied)
        return
    url = _url()
    connect_args = {} if url.startswith("sqlite") else {"connect_timeout": 5}
    engine = create_engine(url, poolclass=NullPool, connect_args=connect_args)
    try:
        with engine.connect() as connection:
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
