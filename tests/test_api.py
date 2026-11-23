"""Tests des endpoints de l'API."""

import pytest


class TestHealth:
    """Tests du endpoint /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "model_loaded" in data
        assert "environment" in data
        assert "version" in data
        assert data["database"] == "ok"
        assert data["model_version"].startswith("logreg-")

    def test_health_model_loaded(self, client):
        data = client.get("/health").json()
        assert data["model_loaded"] is True


class TestPredict:
    """Tests du endpoint POST /predict/."""

    def test_predict_returns_200(self, client, api_key, sample_employee_data):
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200

    def test_predict_response_structure(self, client, api_key, sample_employee_data):
        data = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        ).json()
        assert "probability" in data
        assert "prediction" in data
        assert "risk_level" in data
        assert "threshold" in data

    def test_predict_probability_range(self, client, api_key, sample_employee_data):
        data = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        ).json()
        assert 0 <= data["probability"] <= 1

    def test_predict_prediction_binary(self, client, api_key, sample_employee_data):
        data = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        ).json()
        assert data["prediction"] in [0, 1]

    def test_predict_risk_level_valid(self, client, api_key, sample_employee_data):
        data = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        ).json()
        assert data["risk_level"] in ["faible", "modéré", "élevé", "critique"]

    def test_predict_high_risk_employee(self, client, api_key, sample_employee_data):
        """Un employé jeune, célibataire, avec heures sup devrait avoir un risque élevé."""
        data = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        ).json()
        assert data["probability"] > 0.3

    def test_predict_low_risk_employee(self, client, api_key, sample_low_risk_employee):
        """Un senior marié sans heures sup devrait avoir un faible risque."""
        data = client.post(
            "/predict/",
            json=sample_low_risk_employee,
            headers={"X-API-Key": api_key},
        ).json()
        assert data["probability"] < 0.5


class TestAuth:
    """Tests de l'authentification par clé API et du contrôle d'accès."""

    def test_missing_api_key_returns_401(self, client, sample_employee_data):
        response = client.post("/predict/", json=sample_employee_data)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "ApiKey"

    def test_invalid_api_key_returns_401(self, client, sample_employee_data):
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_revoked_api_key_returns_401(self, client, api_key, db_session, sample_employee_data):
        from datetime import UTC, datetime

        from app.models.database import ApiClient

        db_session.query(ApiClient).update({"revoked_at": datetime.now(UTC)})
        db_session.commit()
        response = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 401

    def test_valid_api_key_returns_200(self, client, api_key, sample_employee_data):
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200

    def test_logs_forbidden_for_predict_role(self, client, api_key):
        response = client.get("/predict/logs", headers={"X-API-Key": api_key})
        assert response.status_code == 403

    def test_logs_allowed_for_admin(self, client, admin_api_key):
        response = client.get("/predict/logs", headers={"X-API-Key": admin_api_key})
        assert response.status_code == 200

    def test_api_key_never_stored_in_clear(self, api_key, db_session):
        from app.models.database import ApiClient

        stored = [c.key_hash for c in db_session.query(ApiClient).all()]
        assert api_key not in stored
        assert all(len(h) == 64 for h in stored)


class TestValidation:
    """Tests de la validation Pydantic des données d'entrée."""

    def test_invalid_age_too_young(self, client, api_key, sample_employee_data):
        sample_employee_data["age"] = 10
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422

    def test_invalid_genre(self, client, api_key, sample_employee_data):
        sample_employee_data["genre"] = "X"
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422

    def test_invalid_satisfaction_out_of_range(self, client, api_key, sample_employee_data):
        sample_employee_data["satisfaction_employee_environnement"] = 5
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422

    def test_missing_required_field(self, client, api_key):
        response = client.post(
            "/predict/",
            json={"age": 30},
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422

    def test_negative_revenue(self, client, api_key, sample_employee_data):
        sample_employee_data["revenu_mensuel"] = -1000
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("field", "value"),
        [("poste", "Astronaute"), ("domaine_etude", "Cuisine"), ("statut_marital", "Pacsé(e)")],
    )
    def test_unknown_category_rejected(self, client, api_key, sample_employee_data, field, value):
        """Une modalité inconnue doit être rejetée, pas encodée silencieusement."""
        sample_employee_data[field] = value
        response = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("age", [17, 71])
    def test_age_boundaries_rejected(self, client, api_key, sample_employee_data, age):
        sample_employee_data["age"] = age
        response = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("age", [18, 70])
    def test_age_boundaries_accepted(self, client, api_key, sample_employee_data, age):
        sample_employee_data["age"] = age
        response = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("limit", [0, -1, 501])
    def test_logs_limit_bounds(self, client, admin_api_key, limit):
        response = client.get(
            "/predict/logs", params={"limit": limit}, headers={"X-API-Key": admin_api_key}
        )
        assert response.status_code == 422


class TestTraceability:
    """Toute interaction avec le modèle est tracée en base (tests fonctionnels)."""

    def test_success_logs_request_and_prediction(
        self, client, api_key, admin_api_key, sample_employee_data
    ):
        result = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        ).json()
        logs = client.get("/predict/logs", headers={"X-API-Key": admin_api_key}).json()
        log = next(entry for entry in logs if entry["id"] == result["request_id"])
        assert log["status"] == "success"
        assert log["payload"] == sample_employee_data
        assert log["prediction"]["probability"] == result["probability"]
        assert log["prediction"]["model_version"] == result["model_version"]
        assert log["client_id"] is not None
        assert log["latency_ms"] >= 0

    def test_rejected_request_is_logged(self, client, api_key, admin_api_key, sample_employee_data):
        sample_employee_data["age"] = 10
        client.post("/predict/", json=sample_employee_data, headers={"X-API-Key": api_key})
        logs = client.get("/predict/logs", headers={"X-API-Key": admin_api_key}).json()
        rejected = [entry for entry in logs if entry["status"] == "rejected"]
        assert len(rejected) == 1
        assert rejected[0]["prediction"] is None
        assert rejected[0]["payload"]["age"] == 10
        assert rejected[0]["client_id"] is not None

    def test_model_error_is_logged_and_returns_500(
        self, client, api_key, admin_api_key, sample_employee_data, monkeypatch
    ):
        from app.services.prediction import get_prediction_service

        def boom(_employee):
            raise RuntimeError("artefact corrompu")

        monkeypatch.setattr(get_prediction_service(), "predict", boom)
        response = client.post(
            "/predict/", json=sample_employee_data, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 500
        monkeypatch.undo()
        logs = client.get("/predict/logs", headers={"X-API-Key": admin_api_key}).json()
        assert [entry["status"] for entry in logs] == ["error"]
        assert "artefact corrompu" in logs[0]["error_detail"]

    def test_predict_for_employee_in_database(self, client, api_key, db_session):
        from sqlalchemy import insert

        from app.models.database import Employee, PredictionRequest
        from scripts.insert_dataset import load_and_join, to_records

        db_session.execute(insert(Employee), to_records(load_and_join().head(3)))
        db_session.commit()
        response = client.post("/predict/employees/1", headers={"X-API-Key": api_key})
        assert response.status_code == 200
        req = db_session.get(PredictionRequest, response.json()["request_id"])
        assert req.employee_id == 1

    def test_predict_for_unknown_employee_returns_404(self, client, api_key):
        response = client.post("/predict/employees/99999", headers={"X-API-Key": api_key})
        assert response.status_code == 404
