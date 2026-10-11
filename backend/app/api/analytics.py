import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.schemas.analytics import AnalyticsSummary
from backend.app.services.analytics_service import build_summary

router = APIRouter(
    prefix="/api",
    tags=["Analytics"],
)


def require_analytics_key(
    x_analytics_key: str | None = Header(
        default=None,
        alias="X-Analytics-Key",
    ),
) -> None:
    configured_key = settings.analytics_api_key

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "analytics_disabled",
                "message": "ANALYTICS_API_KEY n'est pas configurée.",
            },
        )

    if not x_analytics_key or not secrets.compare_digest(
        x_analytics_key, configured_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_analytics_key",
                "message": "Clé d'accès aux statistiques absente ou invalide.",
            },
        )


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    dependencies=[Depends(require_analytics_key)],
)
def get_analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    return AnalyticsSummary.model_validate(build_summary(db, days=days))
