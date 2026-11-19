from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from alembic import command
from app.core.config import get_settings
from app.database.base import NAMING_CONVENTION, Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def test_base_metadata_registers_models_with_constraint_names() -> None:
    class MetadataParent(Base):
        __tablename__ = "migration_metadata_parent"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class MetadataProbe(Base):
        __tablename__ = "migration_metadata_probe"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        slug: Mapped[str] = mapped_column(String(40), unique=True)
        parent_id: Mapped[int] = mapped_column(
            ForeignKey("migration_metadata_parent.id"), index=True
        )

    class TimestampProbe(Base, TimestampMixin, SoftDeleteMixin):
        __tablename__ = "migration_timestamp_probe"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)

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
        foreign_key = next(iter(table.foreign_key_constraints))
        index = next(iter(table.indexes))
        assert foreign_key.name == (
            "fk_migration_metadata_probe_parent_id_migration_metadata_parent"
        )
        assert index.name == "ix_migration_metadata_probe_parent_id"
        timestamp_table = Base.metadata.tables["migration_timestamp_probe"]
        assert timestamp_table.c.created_at.type.timezone is True
        assert timestamp_table.c.updated_at.type.timezone is True
        assert timestamp_table.c.deleted_at.nullable is True
    finally:
        Base.metadata.remove(TimestampProbe.__table__)
        Base.metadata.remove(MetadataProbe.__table__)
        Base.metadata.remove(MetadataParent.__table__)


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


def test_alembic_offline_upgrade_uses_environment_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://migration-host/evolvus360")
    get_settings.cache_clear()
    try:
        command.upgrade(alembic_config(), "head", sql=True)
    finally:
        get_settings.cache_clear()

    sql_output = capsys.readouterr().out
    assert "CREATE TABLE alembic_version" in sql_output
    assert "0001_initial_baseline" in sql_output


def test_migration_discovery_finds_hrms_head_and_preserves_baseline() -> None:
    scripts = ScriptDirectory.from_config(alembic_config())

    assert len(scripts.get_heads()) == 1
    revision = scripts.get_revision(scripts.get_heads()[0])
    assert revision is not None
    assert revision.revision == "a7d9c2e84b16"
    assert revision.down_revision == "f731c2d89a04"
    assert scripts.get_revision("0001_initial_baseline").down_revision is None


def test_relational_restore_migrates_legacy_master_rows_before_drop() -> None:
    scripts = ScriptDirectory.from_config(alembic_config())
    revision = scripts.get_revision("c4a17e63d29b")
    assert revision is not None
    source = Path(revision.module.__file__).read_text(encoding="utf-8")

    assert "master_data is expected to remain absent" not in source
    assert "WHERE group_type = 'mst-roles'" in source
    assert "WHERE group_type = 'mst-permissions'" in source
    assert "WHERE group_type = 'mst-menus'" in source
    assert "is_deleted, created_at, updated_at" in source
    assert "Cannot safely restore departments/entities" in source
    assert "EXECUTE 'DROP TABLE public.master_data'" in source


def test_application_has_no_master_data_table_dependency() -> None:
    app_dir = BACKEND_DIR / "app"
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in app_dir.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    )

    assert "public.master_data" not in source_text
    assert "FROM master_data" not in source_text
    assert "JOIN master_data" not in source_text


def test_password_reset_revision_has_reversible_migration_functions() -> None:
    scripts = ScriptDirectory.from_config(alembic_config())
    revision = scripts.get_revision("b8e683b32e35")
    assert revision is not None
    assert callable(revision.module.upgrade)
    assert callable(revision.module.downgrade)
    source = revision.module.__file__
    assert source is not None
    migration = Path(source).read_text(encoding="utf-8")
    assert "op.create_table(" in migration
    assert '"password_reset_tokens"' in migration
    assert 'op.drop_table("password_reset_tokens"' in migration


def test_application_does_not_run_migrations_automatically() -> None:
    main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")

    assert "alembic" not in main_source.lower()
    assert "upgrade(" not in main_source
