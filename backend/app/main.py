from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.db.connector import report_connection_at_startup
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    report_connection_at_startup()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api")
