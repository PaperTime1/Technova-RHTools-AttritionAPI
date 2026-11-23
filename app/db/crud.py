"""Opérations CRUD sur la base de données (requêtes paramétrées via l'ORM)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.database import ApiClient, Employee, Prediction, PredictionRequest
from app.models.schemas import PredictionOutput
from app.security import hash_api_key

# ── Traçabilité des requêtes ──


def create_request(
    db: Session,
    payload: dict,
    status: str,
    client_id: int | None = None,
    employee_id: int | None = None,
    error_detail: str | None = None,
    latency_ms: float | None = None,
) -> PredictionRequest:
    """Enregistre une requête reçue sur /predict (quel que soit son statut)."""
    req = PredictionRequest(
        payload=payload,
        status=status,
        client_id=client_id,
        employee_id=employee_id,
        error_detail=error_detail,
        latency_ms=latency_ms,
    )
    db.add(req)
    db.flush()  # attribue l'id sans clore la transaction
    return req


def log_prediction(
    db: Session,
    payload: dict,
    output: PredictionOutput,
    client_id: int | None = None,
    employee_id: int | None = None,
    latency_ms: float | None = None,
) -> PredictionRequest:
    """Enregistre une requête réussie ET sa prédiction, dans la même transaction."""
    req = create_request(
        db, payload, "success", client_id=client_id, employee_id=employee_id, latency_ms=latency_ms
    )
    req.prediction = Prediction(
        probability=output.probability,
        predicted_label=output.prediction,
        risk_level=output.risk_level,
        threshold=output.threshold,
        model_version=output.model_version,
    )
    db.flush()
    return req


def get_prediction_logs(db: Session, limit: int = 50) -> list[PredictionRequest]:
    """Dernières requêtes, avec leur prédiction éventuelle (plus récentes d'abord)."""
    stmt = (
        select(PredictionRequest)
        .options(selectinload(PredictionRequest.prediction))
        .order_by(PredictionRequest.created_at.desc(), PredictionRequest.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


# ── Employés (dataset de référence) ──


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def get_employees(db: Session, skip: int = 0, limit: int = 100) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.id).offset(skip).limit(limit)))


def get_employee_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Employee)) or 0


# ── Clients de l'API ──


def create_api_client(db: Session, name: str, api_key: str, role: str = "predict") -> ApiClient:
    """Crée un client ; seule l'empreinte de la clé est stockée."""
    client = ApiClient(name=name, key_hash=hash_api_key(api_key), role=role)
    db.add(client)
    db.flush()
    return client
