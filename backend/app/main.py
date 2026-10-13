import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Dataset, User
from app.services.users import seed_initial_admin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if engine.dialect.name == "sqlite":
        # Local development without PostgreSQL: create the account and dataset
        # tables directly (PostGIS-backed tables are not used on SQLite).
        Base.metadata.create_all(
            engine, tables=[cast(Table, User.__table__), cast(Table, Dataset.__table__)]
        )
    try:
        with SessionLocal() as db:
            seed_initial_admin(db)
    except SQLAlchemyError:
        logger.exception("Could not seed the initial administrator (run `alembic upgrade head`).")
    yield


# Debug mode returns tracebacks for unhandled errors; never in production.
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG and settings.APP_ENV != "production",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
