"""Endpoints de prédiction d'attrition.

Toute interaction avec le modèle passe par la base : la requête (input brut, appelant,
statut, latence) et la prédiction (probabilité, décision, seuil, version du modèle) sont
enregistrées dans la même transaction que la réponse.

Les routes sont synchrones (def) : la prédiction scikit-learn et le driver PostgreSQL sont
bloquants ; FastAPI les exécute dans un pool de threads sans bloquer la boucle d'événements.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.models.database import ApiClient
from app.models.schemas import EmployeeInput, PredictionLog, PredictionOutput
from app.security import get_current_client, require_admin
from app.services.prediction import get_prediction_service

router = APIRouter(prefix="/predict", tags=["Prédictions"])

_AUTH_RESPONSES = {
    401: {"description": "Clé d'API manquante, invalide ou révoquée"},
    422: {"description": "Données d'entrée invalides (requête tracée avec le statut 'rejected')"},
    500: {"description": "Erreur interne (requête tracée avec le statut 'error')"},
}


def _predict_and_log(
    db: Session, employee: EmployeeInput, client: ApiClient, employee_id: int | None
) -> PredictionOutput:
    payload = employee.model_dump(mode="json")
    start = time.perf_counter()
    try:
        result = get_prediction_service().predict(employee)
    except Exception as exc:
        # L'échec est tracé et validé AVANT de renvoyer l'erreur (sinon il serait annulé)
        crud.create_request(
            db,
            payload,
            "error",
            client_id=client.id,
            employee_id=employee_id,
            error_detail=f"{type(exc).__name__}: {exc}",
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la prédiction"
        ) from exc

    req = crud.log_prediction(
        db,
        payload,
        result,
        client_id=client.id,
        employee_id=employee_id,
        latency_ms=(time.perf_counter() - start) * 1000,
    )
    return result.model_copy(update={"request_id": req.id})


@router.post(
    "/",
    response_model=PredictionOutput,
    summary="Prédire le risque d'attrition à partir de données saisies",
    description="Envoie le profil d'un employé et reçoit la probabilité de départ, la décision "
    "binaire (au seuil métier), le niveau de risque et la version du modèle. "
    "La requête et la prédiction sont enregistrées en base.",
    responses=_AUTH_RESPONSES,
)
def predict_attrition(
    employee: EmployeeInput,
    employee_id: int | None = Query(
        None, ge=1, description="Identifiant de l'employé concerné, s'il est connu en base"
    ),
    client: ApiClient = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> PredictionOutput:
    if employee_id is not None and crud.get_employee(db, employee_id) is None:
        raise HTTPException(status_code=404, detail=f"Employé {employee_id} inconnu")
    return _predict_and_log(db, employee, client, employee_id)


@router.post(
    "/employees/{employee_id}",
    response_model=PredictionOutput,
    summary="Prédire le risque d'attrition d'un employé de la base",
    description="Lit le profil de l'employé dans la table employees, le score avec le modèle "
    "et trace la requête en la reliant à l'employé (clé étrangère).",
    responses={**_AUTH_RESPONSES, 404: {"description": "Employé inconnu"}},
)
def predict_for_employee(
    employee_id: int = Path(..., ge=1),
    client: ApiClient = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> PredictionOutput:
    row = crud.get_employee(db, employee_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Employé {employee_id} inconnu")
    employee = EmployeeInput.model_validate(
        {field: getattr(row, field) for field in EmployeeInput.model_fields}
    )
    return _predict_and_log(db, employee, client, employee_id)


@router.get(
    "/logs",
    response_model=list[PredictionLog],
    summary="Historique des requêtes et prédictions (admin)",
    description="Retourne les dernières requêtes tracées, avec leur prédiction. "
    "Réservé au rôle 'admin' : les payloads contiennent des données personnelles.",
    responses={401: _AUTH_RESPONSES[401], 403: {"description": "Rôle 'admin' requis"}},
)
def prediction_history(
    limit: int = Query(50, ge=1, le=500, description="Nombre maximal de requêtes renvoyées"),
    _admin: ApiClient = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[PredictionLog]:
    return crud.get_prediction_logs(db, limit=limit)
