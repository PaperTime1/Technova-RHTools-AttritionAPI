"""Endpoints de prédiction d'attrition."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.crud import get_prediction_logs, log_prediction
from app.db.session import get_db
from app.models.schemas import EmployeeInput, PredictionLog, PredictionOutput
from app.services.prediction import get_prediction_service

router = APIRouter(prefix="/predict", tags=["Prédictions"])


def verify_api_key(x_api_key: str = Header(..., description="Clé API pour l'authentification")):
    """Vérifie la clé API dans le header X-API-Key."""
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return x_api_key


@router.post(
    "/",
    response_model=PredictionOutput,
    summary="Prédire le risque d'attrition d'un employé",
    description="Envoie les données d'un employé et reçoit la probabilité de départ, "
    "la prédiction binaire et le niveau de risque.",
)
async def predict_attrition(
    employee: EmployeeInput,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Endpoint principal de prédiction."""
    service = get_prediction_service()
    result = service.predict(employee)

    # Log en base pour la traçabilité
    log_prediction(db, employee.model_dump(), result)

    return result


@router.get(
    "/logs",
    response_model=list[PredictionLog],
    summary="Historique des prédictions",
    description="Retourne les 50 dernières prédictions effectuées.",
)
async def prediction_history(
    limit: int = 50,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Récupère l'historique des prédictions."""
    return get_prediction_logs(db, limit=limit)
