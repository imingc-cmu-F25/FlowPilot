from fastapi import APIRouter

from app.core.config import settings

api_router = APIRouter()


@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
