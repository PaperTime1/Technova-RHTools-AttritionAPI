"""Tests du pipeline de preprocessing."""

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import EmployeeInput
from app.services.prediction import get_prediction_service
from app.services.preprocessing import (
    employee_to_dataframe,
    encode_features,
    engineer_features,
    preprocess_input,
)


class TestEmployeeToDataframe:
    """Tests de la conversion Pydantic → DataFrame."""

    def test_returns_dataframe(self, sample_employee_data):
        employee = EmployeeInput(**sample_employee_data)
        df = employee_to_dataframe(employee)
        assert isinstance(df, pd.DataFrame)

    def test_single_row(self, sample_employee_data):
        employee = EmployeeInput(**sample_employee_data)
        df = employee_to_dataframe(employee)
        assert len(df) == 1

    def test_all_fields_present(self, sample_employee_data):
        employee = EmployeeInput(**sample_employee_data)
        df = employee_to_dataframe(employee)
        for key in sample_employee_data:
            assert key in df.columns


class TestEngineerFeatures:
    """Tests du feature engineering."""

    def test_adds_satisfaction_moyenne(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = engineer_features(df)
        assert "satisfaction_moyenne" in result.columns

    def test_satisfaction_moyenne_value(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = engineer_features(df)
        expected = np.mean(
            [
                sample_employee_data["satisfaction_employee_environnement"],
                sample_employee_data["satisfaction_employee_nature_travail"],
                sample_employee_data["satisfaction_employee_equipe"],
                sample_employee_data["satisfaction_employee_equilibre_pro_perso"],
            ]
        )
        assert result["satisfaction_moyenne"].iloc[0] == pytest.approx(expected)

    def test_adds_anciennete_vs_experience(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = engineer_features(df)
        assert "anciennete_vs_experience" in result.columns

    def test_anciennete_ratio_zero_xp(self, sample_employee_data):
        """Si 0 ans d'XP, le ratio doit être 0 (pas de division par zéro)."""
        sample_employee_data["annee_experience_totale"] = 0
        df = pd.DataFrame([sample_employee_data])
        result = engineer_features(df)
        assert result["anciennete_vs_experience"].iloc[0] == 0.0

    def test_adds_revenu_par_annee_xp(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = engineer_features(df)
        assert "revenu_par_annee_xp" in result.columns


class TestEncodeFeatures:
    """Tests de l'encoding catégoriel."""

    def test_genre_encoded(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = encode_features(df)
        assert result["genre"].iloc[0] in [0, 1]

    def test_heure_sup_encoded(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = encode_features(df)
        assert result["heure_supplementaires"].iloc[0] in [0, 1]

    def test_no_object_columns(self, sample_employee_data):
        df = pd.DataFrame([sample_employee_data])
        result = encode_features(df)
        assert result.select_dtypes(include="object").shape[1] == 0

    def test_ohe_creates_columns(self, sample_employee_data):
        """Vérifie que l'OHE crée des colonnes pour les catégorielles."""
        df = pd.DataFrame([sample_employee_data])
        result = encode_features(df)
        # Après OHE, les colonnes originales (str) ne doivent plus exister
        assert "statut_marital" not in result.columns
        assert "poste" not in result.columns
        assert "domaine_etude" not in result.columns
        # Et il ne doit rester aucune colonne object
        assert result.select_dtypes(include="object").shape[1] == 0


class TestPreprocessInput:
    """Tests du pipeline complet."""

    def test_returns_numpy_array(self, sample_employee_data):
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = preprocess_input(employee, service.features, service.scaler)
        assert isinstance(result, np.ndarray)

    def test_correct_shape(self, sample_employee_data):
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = preprocess_input(employee, service.features, service.scaler)
        assert result.shape == (1, len(service.features))

    def test_no_nan_in_output(self, sample_employee_data):
        service = get_prediction_service()
        employee = EmployeeInput(**sample_employee_data)
        result = preprocess_input(employee, service.features, service.scaler)
        assert not np.isnan(result).any()
