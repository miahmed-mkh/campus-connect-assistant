from fastapi import FastAPI

from backend.app.api.chat import router as chat_router
from backend.app.core.config import settings

from backend.app.api.feedback import router as feedback_router



app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(chat_router)

app.include_router(feedback_router)

@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "status": "running",
        "environment": settings.app_environment,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_environment,
    }
