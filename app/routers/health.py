"""Endpoint de santé de l'API (utilisé par le HEALTHCHECK Docker et le smoke test CI/CD)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.config import get_settings
from app.db.session import get_db
from app.models.schemas import HealthResponse
from app.services.prediction import get_prediction_service

router = APIRouter(tags=["Santé"])


@router.get("/health", response_model=HealthResponse, summary="Vérifier l'état de l'API")
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """État du modèle et de la base. 'degraded' si l'un des deux est indisponible."""
    try:
        service = get_prediction_service()
        model_loaded, model_version = service.is_loaded, service.model_version
    except Exception:
        model_loaded, model_version = False, None

    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"

    return HealthResponse(
        status="ok" if model_loaded and database == "ok" else "degraded",
        environment=get_settings().environment,
        model_loaded=model_loaded,
        database=database,
        model_version=model_version,
        version=__version__,
    )
