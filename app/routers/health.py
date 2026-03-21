"""Endpoint de santé de l'API."""

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services.prediction import get_prediction_service

router = APIRouter(tags=["Santé"])


@router.get("/health", response_model=HealthResponse, summary="Vérifier l'état de l'API")
async def health_check():
    """Retourne l'état de l'API et du modèle."""
    settings = get_settings()
    try:
        service = get_prediction_service()
        model_loaded = service.is_loaded
    except Exception:
        model_loaded = False

    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        environment=settings.environment,
        model_loaded=model_loaded,
    )
