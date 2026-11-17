"""Shared synchronous SQLAlchemy engine and per-request sessions."""

import logging
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database operation is attempted without DATABASE_URL."""


class RequestSession(Session):
    """Allow one service-owned commit per request session.

    The service convention uses one transaction commit at the service boundary.
    Nested savepoints remain available; separate independently committed units
    should use separate sessions so a partial request cannot be committed twice.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._commit_performed = False

    def commit(self) -> None:
        if self._commit_performed:
            raise InvalidRequestError(
                "A request session may be committed only once; "
                "service owns the transaction"
            )
        super().commit()


@event.listens_for(RequestSession, "after_commit")
def _record_completed_request_commit(session: RequestSession) -> None:
    """Track root commits, including those made through ``Session.begin()``."""
    if not session.in_nested_transaction():
        session._commit_performed = True


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and reuse the process-wide engine using configured pool limits."""
    settings = get_settings()
    if not settings.database_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL must be configured before database use"
        )

    options: dict[str, object] = {"pool_pre_ping": settings.db_pool_pre_ping}
    if not settings.database_url.startswith("sqlite"):
        options["connect_args"] = {
            "connect_timeout": settings.db_connect_timeout_seconds
        }
        options.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
        )
    return create_engine(settings.database_url, **options)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[RequestSession]:
    """Return the shared factory; sessions are created per request."""
    return sessionmaker(
        bind=get_engine(),
        class_=RequestSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def SessionLocal() -> Session:
    """Create a session from the shared factory (never a new engine)."""
    return get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    """Yield one session per request and always rollback failures and close."""
    db = SessionLocal()
    try:
        yield db
    except BaseException:
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to roll back request database session")
        raise
    finally:
        db.close()
