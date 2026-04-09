from fastapi import APIRouter

from app.core.config import settings
from app.user.router import router as user_router

api_router = APIRouter()


@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}

api_router.include_router(user_router, prefix="/users", tags=["users"])