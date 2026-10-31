"""Health check route (no database access, no sensitive data)."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health check")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
