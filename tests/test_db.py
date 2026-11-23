"""Tests de la base de données : opérations CRUD, intégrité des données, contraintes."""

import pytest
from sqlalchemy import insert, inspect
from sqlalchemy.exc import IntegrityError

from app.db.crud import (
    create_api_client,
    create_request,
    get_employee,
    get_employee_count,
    get_employees,
    get_prediction_logs,
    log_prediction,
)
from app.models.database import Employee, Prediction, PredictionRequest
from app.models.schemas import PredictionOutput
from scripts.insert_dataset import insert_employees, load_and_join, to_records


def _output(probability: float = 0.75, prediction: int = 1) -> PredictionOutput:
    return PredictionOutput(
        probability=probability,
        prediction=prediction,
        risk_level="élevé" if prediction else "faible",
        threshold=0.328,
        model_version="logreg-test",
    )


class TestPredictionLogs:
    """Traçabilité des requêtes et des prédictions."""

    def test_log_prediction_creates_request_and_prediction(self, db_session):
        req = log_prediction(db_session, {"age": 30, "genre": "M"}, _output())
        db_session.commit()
        assert req.id is not None
        assert req.status == "success"
        assert req.prediction.probability == 0.75
        assert req.prediction.predicted_label == 1
        assert req.prediction.model_version == "logreg-test"

    def test_log_stores_input_data(self, db_session):
        payload = {"age": 35, "genre": "F", "poste": "Consultant"}
        req = log_prediction(db_session, payload, _output(0.45))
        db_session.commit()
        db_session.expire_all()
        stored = db_session.get(PredictionRequest, req.id)
        assert stored.payload == payload

    def test_log_has_timestamp(self, db_session):
        req = log_prediction(db_session, {}, _output(0.10, 0))
        db_session.commit()
        db_session.refresh(req)
        assert req.created_at is not None

    def test_get_logs_ordered_and_limited(self, db_session):
        for prob in [0.1, 0.5, 0.9]:
            log_prediction(db_session, {"p": prob}, _output(prob, int(prob >= 0.328)))
        db_session.commit()
        logs = get_prediction_logs(db_session, limit=2)
        assert len(logs) == 2
        assert [log.payload["p"] for log in logs] == [0.9, 0.5]  # plus récentes d'abord

    def test_rejected_request_has_no_prediction(self, db_session):
        req = create_request(db_session, {"age": 10}, "rejected", error_detail="age < 18")
        db_session.commit()
        assert req.prediction is None


class TestIntegrity:
    """Contraintes garanties par le SGBD (et non seulement par l'application)."""

    def test_probability_out_of_range_rejected(self, db_session):
        req = create_request(db_session, {}, "success")
        db_session.add(
            Prediction(
                request_id=req.id,
                probability=1.5,
                predicted_label=1,
                risk_level="critique",
                threshold=0.328,
                model_version="v",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_invalid_status_rejected(self, db_session):
        db_session.add(PredictionRequest(payload={}, status="unknown"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_one_prediction_per_request(self, db_session):
        req = log_prediction(db_session, {}, _output())
        db_session.add(
            Prediction(
                request_id=req.id,
                probability=0.2,
                predicted_label=0,
                risk_level="modéré",
                threshold=0.328,
                model_version="v",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_foreign_key_to_unknown_employee_rejected(self, db_session):
        db_session.add(PredictionRequest(payload={}, status="success", employee_id=123456))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_duplicate_api_client_name_rejected(self, db_session):
        create_api_client(db_session, "dup", "key-1")
        with pytest.raises(IntegrityError):
            create_api_client(db_session, "dup", "key-2")

    def test_deleting_request_cascades_to_prediction(self, db_session):
        req = log_prediction(db_session, {}, _output())
        db_session.commit()
        db_session.delete(req)
        db_session.commit()
        assert db_session.query(Prediction).count() == 0


class TestEmployeeTable:
    """Table employees : schéma et insertion du dataset."""

    def test_schema_has_expected_tables(self, db_session):
        tables = set(inspect(db_session.get_bind()).get_table_names())
        assert {"employees", "api_clients", "prediction_requests", "predictions"} <= tables

    def test_employee_has_required_columns(self):
        columns = {c.name for c in Employee.__table__.columns}
        assert {"id", "age", "genre", "revenu_mensuel", "attrition"} <= columns

    def test_dataset_join_is_complete(self):
        df = load_and_join()
        assert len(df) == 1470
        assert df["id_employee"].is_unique
        assert df["attrition"].sum() == 237

    def test_insert_full_dataset(self, db_session, monkeypatch):
        """Insertion des 1 470 employés en une transaction, puis idempotence."""
        from tests.conftest import TestSessionLocal

        monkeypatch.setattr("scripts.insert_dataset.get_session_factory", lambda: TestSessionLocal)
        df = load_and_join()
        assert insert_employees(df) == 1470
        assert insert_employees(df) == 1470  # deuxième appel : rien n'est réinséré
        assert get_employee_count(db_session) == 1470
        assert get_employee(db_session, 1).age == df.loc[df["id_employee"] == 1, "age"].item()
        assert len(get_employees(db_session, skip=0, limit=10)) == 10

    def test_invalid_employee_rejected(self, db_session):
        record = to_records(load_and_join().head(1))[0]
        record["age"] = 12
        with pytest.raises(IntegrityError):
            db_session.execute(insert(Employee), [record])
