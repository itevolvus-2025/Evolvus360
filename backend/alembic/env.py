"""Alembic runtime environment using application settings and model metadata."""

from logging.config import fileConfig

from sqlalchemy import Connection, create_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  # Import model modules so metadata is populated.
from alembic import context
from app.core.config import get_settings
from app.database.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

settings = get_settings()
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Keep HRMS autogeneration scoped to tables in HRMS model metadata."""
    if type_ == "table":
        return name in target_metadata.tables
    return True

if settings.database_url:
    # ConfigParser treats percent signs as interpolation markers.
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured for Alembic migrations")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
        version_table="alembic_version",
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
        version_table="alembic_version",
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        _run_migrations(supplied_connection)
        return

    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured for Alembic migrations")

    connect_args = {}
    if not database_url.startswith("sqlite"):
        connect_args["connect_timeout"] = settings.db_connect_timeout_seconds
    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args=connect_args,
    )
    try:
        with engine.connect() as connection:
            _run_migrations(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
