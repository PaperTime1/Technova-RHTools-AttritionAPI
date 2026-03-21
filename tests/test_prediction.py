"""Tests du service de prédiction."""

import pytest
from app.services.prediction import get_prediction_service, PredictionService
from app.models.schemas import EmployeeInput


class TestPredictionService:
    """Tests du service de prédiction ML."""

    def test_service_loads(self):
        service = get_prediction_service()
        assert service.is_loaded

    def test_service_has_features(self):
        service = get_prediction_service()
        assert len(service.features) > 0

    def test_service_has_threshold(self):
        service = get_prediction_service()
        assert 0 < service.threshold < 1

    def test_predict_returns_prediction_output(self, sample_employee_data):
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = service.predict(employee)
        assert hasattr(result, "probability")
        assert hasattr(result, "prediction")
        assert hasattr(result, "risk_level")

    def test_predict_probability_in_range(self, sample_employee_data):
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = service.predict(employee)
        assert 0 <= result.probability <= 1

    def test_predict_consistent_with_threshold(self, sample_employee_data):
        """La prédiction binaire doit être cohérente avec le seuil."""
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = service.predict(employee)

        if result.probability >= service.threshold:
            assert result.prediction == 1
        else:
            assert result.prediction == 0

    def test_risk_levels_ordering(self):
        """Vérifier que les niveaux de risque sont cohérents."""
        service = get_prediction_service()
        assert service._compute_risk_level(0.05) == "faible"
        assert service._compute_risk_level(0.20) == "modéré"
        assert service._compute_risk_level(0.45) == "élevé"
        assert service._compute_risk_level(0.75) == "critique"

    def test_different_profiles_different_predictions(
        self, sample_employee_data, sample_low_risk_employee
    ):
        """Deux profils différents doivent avoir des probabilités différentes."""
        service = get_prediction_service()
        high_risk = EmployeeInput(**sample_employee_data)
        low_risk = EmployeeInput(**sample_low_risk_employee)

        result_high = service.predict(high_risk)
        result_low = service.predict(low_risk)

        assert result_high.probability != result_low.probability
