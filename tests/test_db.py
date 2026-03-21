"""Tests des opérations sur la base de données."""

import pytest
from app.models.database import PredictionLogDB, Employee
from app.models.schemas import PredictionOutput
from app.db.crud import log_prediction, get_prediction_logs


class TestPredictionLogs:
    """Tests du logging des prédictions en BDD."""

    def test_log_prediction_creates_record(self, db_session):
        output = PredictionOutput(
            probability=0.75,
            prediction=1,
            risk_level="élevé",
            threshold=0.328,
        )
        log = log_prediction(db_session, {"age": 30, "genre": "M"}, output)
        assert log.id is not None
        assert log.probability == 0.75
        assert log.prediction == 1
        assert log.risk_level == "élevé"

    def test_log_stores_input_data(self, db_session):
        input_data = {"age": 35, "genre": "F", "poste": "Consultant"}
        output = PredictionOutput(
            probability=0.45,
            prediction=1,
            risk_level="élevé",
            threshold=0.328,
        )
        log = log_prediction(db_session, input_data, output)
        assert log.input_data["age"] == 35
        assert log.input_data["genre"] == "F"

    def test_log_has_timestamp(self, db_session):
        output = PredictionOutput(
            probability=0.10,
            prediction=0,
            risk_level="faible",
            threshold=0.328,
        )
        log = log_prediction(db_session, {}, output)
        assert log.timestamp is not None

    def test_get_logs_returns_list(self, db_session):
        # Insérer quelques logs
        for prob in [0.1, 0.5, 0.9]:
            output = PredictionOutput(
                probability=prob,
                prediction=int(prob >= 0.328),
                risk_level="test",
                threshold=0.328,
            )
            log_prediction(db_session, {"test": True}, output)

        logs = get_prediction_logs(db_session, limit=10)
        assert isinstance(logs, list)
        assert len(logs) >= 3

    def test_get_logs_respects_limit(self, db_session):
        logs = get_prediction_logs(db_session, limit=2)
        assert len(logs) <= 2


class TestEmployeeTable:
    """Tests de la table employees."""

    def test_employee_model_exists(self):
        assert Employee.__tablename__ == "employees"

    def test_employee_has_required_columns(self):
        columns = [c.name for c in Employee.__table__.columns]
        assert "age" in columns
        assert "genre" in columns
        assert "revenu_mensuel" in columns
        assert "attrition" in columns
