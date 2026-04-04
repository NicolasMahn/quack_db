"""Database session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from quack_db.config import get_settings


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args(_settings.database_url),
)

if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_foreign_keys(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
