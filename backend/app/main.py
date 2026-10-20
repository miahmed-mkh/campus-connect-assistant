from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.chat import router as chat_router
from backend.app.core.config import settings
from backend.app.services.semantic_service import start_semantic_warm_up

from backend.app.api.analytics import router as analytics_router
from backend.app.api.auth import router as auth_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.iot import router as iot_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Chargement du modele en arriere-plan : l'API repond tout de suite,
    # avec le moteur lexical seul tant que l'index n'est pas pret.
    start_semantic_warm_up()
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(chat_router)

app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(iot_router)
app.include_router(auth_router)


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
