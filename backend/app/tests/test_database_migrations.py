from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    create_engine,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column

from alembic import command
from app.core.config import get_settings
from app.database.base import NAMING_CONVENTION, Base

BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def test_base_metadata_registers_models_with_constraint_names() -> None:
    class MetadataProbe(Base):
        __tablename__ = "migration_metadata_probe"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        slug: Mapped[str] = mapped_column(String(40), unique=True)

    try:
        assert Base.metadata.naming_convention == NAMING_CONVENTION
        assert "migration_metadata_probe" in Base.metadata.tables
        table = Base.metadata.tables["migration_metadata_probe"]
        unique = next(
            constraint
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        )
        primary_key = next(
            constraint
            for constraint in table.constraints
            if isinstance(constraint, PrimaryKeyConstraint)
        )
        assert unique.name == "uq_migration_metadata_probe_slug"
        assert primary_key.name == "pk_migration_metadata_probe"
    finally:
        Base.metadata.remove(MetadataProbe.__table__)


def test_alembic_config_points_to_migration_directory_without_credentials() -> None:
    config = alembic_config()

    assert (
        Path(config.get_main_option("script_location")).resolve()
        == (BACKEND_DIR / "alembic").resolve()
    )
    assert config.get_main_option("sqlalchemy.url") == ""


def test_alembic_loads_database_url_from_application_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://migration-host/evolvus360"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        assert get_settings().database_url == url
    finally:
        get_settings.cache_clear()


def test_migration_discovery_finds_initial_baseline() -> None:
    scripts = ScriptDirectory.from_config(alembic_config())

    assert scripts.get_heads() == ["0001_initial_baseline"]
    revision = scripts.get_revision("0001_initial_baseline")
    assert revision is not None
    assert revision.down_revision is None


def test_migrations_upgrade_and_downgrade_on_isolated_database() -> None:
    engine = create_engine("sqlite:///:memory:")
    config = alembic_config()
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

            assert inspect(connection).has_table("alembic_version")
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == "0001_initial_baseline"
            )

            command.downgrade(config, "base")
            assert inspect(connection).has_table("alembic_version")
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).fetchall()
                == []
            )
    finally:
        engine.dispose()


def test_application_does_not_run_migrations_automatically() -> None:
    main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")

    assert "alembic" not in main_source.lower()
    assert "upgrade(" not in main_source
