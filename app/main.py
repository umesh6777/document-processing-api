from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import documents, projects
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Fine for an assignment; in production schema changes go through Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=get_settings().app_name, version="1.0.0", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(projects.router)
app.include_router(documents.router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
