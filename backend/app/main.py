from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.connectors.router import router as connectors_router
from app.core.config import settings
from app.db.connector import report_connection_at_startup
from app.db.session import init_db
from app.user.router import router as user_router


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
app.include_router(user_router, prefix="/api/users")
app.include_router(connectors_router, prefix="/api")
