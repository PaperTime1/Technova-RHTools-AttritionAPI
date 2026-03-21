"""Opérations CRUD pour la base de données."""

from sqlalchemy.orm import Session
from app.models.database import PredictionLogDB, Employee
from app.models.schemas import EmployeeInput, PredictionOutput


def log_prediction(
    db: Session,
    input_data: dict,
    output: PredictionOutput,
) -> PredictionLogDB:
    """Enregistre une prédiction en base (traçabilité)."""
    log = PredictionLogDB(
        input_data=input_data,
        probability=output.probability,
        prediction=output.prediction,
        risk_level=output.risk_level,
        threshold_used=output.threshold,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_prediction_logs(db: Session, limit: int = 50) -> list[PredictionLogDB]:
    """Récupère les dernières prédictions."""
    return (
        db.query(PredictionLogDB)
        .order_by(PredictionLogDB.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_employees(db: Session, skip: int = 0, limit: int = 100) -> list[Employee]:
    """Récupère les employés du dataset."""
    return db.query(Employee).offset(skip).limit(limit).all()


def get_employee_count(db: Session) -> int:
    """Compte le nombre d'employés en base."""
    return db.query(Employee).count()
