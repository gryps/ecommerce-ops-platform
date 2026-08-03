from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_engine_url: str | None = None
_engine_lock = Lock()


def database_url() -> str:
    url = settings.workbench_database_url.strip()
    if not url:
        raise RuntimeError("未配置 PVA_WORKBENCH_DATABASE_URL")
    return url


def get_engine() -> Engine:
    global _engine, _session_factory, _engine_url
    url = database_url()
    with _engine_lock:
        if _engine is not None and _engine_url == url:
            return _engine
        if _engine is not None:
            _engine.dispose()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        if url.startswith("sqlite"):
            event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
        _engine_url = url
        return _engine


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_workbench_schema() -> None:
    # Import models before create_all so SQLAlchemy has registered every table.
    from app.domain import models as _models  # noqa: F401

    Base.metadata.create_all(get_engine())


def migrate_workbench_schema() -> None:
    from alembic import command
    from alembic.config import Config

    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url())
    command.upgrade(config, "head")


def reset_engine_for_tests() -> None:
    global _engine, _session_factory, _engine_url
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _session_factory = None
        _engine_url = None
