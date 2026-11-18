"""Database engine and request-scoped SQLAlchemy sessions."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _engine():
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    options = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
        options["connect_args"] = {"connect_timeout": 5}
    return create_engine(url, **options)


_engine_instance = None
_session_factory = None


def get_session_factory():
    global _engine_instance, _session_factory
    if _session_factory is None:
        _engine_instance = _engine()
        _session_factory = sessionmaker(
            bind=_engine_instance,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
