"""FastAPI entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from api.routers import admin, auth_validate, collections, health, rag
from quack_db.config import get_settings

log = logging.getLogger(__name__)


def _run_migrations() -> None:
    s = get_settings()
    if not s.run_migrations_on_startup:
        return
    import quack_db

    ini = Path(quack_db.__file__).resolve().parent.parent / "alembic.ini"
    if not ini.is_file():
        log.warning("alembic.ini not found; skipping migrations")
        return
    cfg = AlembicConfig(str(ini))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    yield


app = FastAPI(title="Quack API", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth_validate.router)
app.include_router(collections.router)
app.include_router(admin.router)
app.include_router(rag.router)
