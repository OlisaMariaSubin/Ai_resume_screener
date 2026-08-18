from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/")
def root():
    settings = get_settings()
    return {
        "service": "AI Resume Screening Assistant",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "frontend": settings.frontend_origin,
    }


@router.get("/health")
def health():
    return {"status": "ok"}
