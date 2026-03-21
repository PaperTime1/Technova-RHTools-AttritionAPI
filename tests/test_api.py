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
    """Tests de l'authentification par clé API."""

    def test_missing_api_key_returns_422(self, client, sample_employee_data):
        response = client.post("/predict/", json=sample_employee_data)
        assert response.status_code == 422

    def test_invalid_api_key_returns_403(self, client, sample_employee_data):
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_valid_api_key_returns_200(self, client, api_key, sample_employee_data):
        response = client.post(
            "/predict/",
            json=sample_employee_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200


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
