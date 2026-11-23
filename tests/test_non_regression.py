"""Test de non-régression : l'API reproduit le modèle du P4 sur tout le dataset.

Référence : l'encodage du notebook P4, c'est-à-dire pd.get_dummies appliqué au
dataset COMPLET (toutes les modalités présentes). Le preprocessing de l'API, appliqué
ligne par ligne comme en production, doit donner exactement les mêmes probabilités.
Ce test aurait détecté le training-serving skew de l'encodage one-hot.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import EmployeeInput
from app.services.prediction import get_prediction_service
from app.services.preprocessing import engineer_features, preprocess_input

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "extrait_sirh.csv").exists(), reason="dataset absent"
)


def _load_dataset() -> pd.DataFrame:
    from scripts.insert_dataset import load_and_join

    return load_and_join(DATA_DIR)


def _reference_probabilities(df: pd.DataFrame, service) -> np.ndarray:
    """Encodage tel que réalisé dans le notebook P4 (sur le dataset complet)."""
    data = engineer_features(df)
    data["genre"] = data["genre"].map({"F": 0, "M": 1})
    data["heure_supplementaires"] = data["heure_supplementaires"].map({"Non": 0, "Oui": 1})
    data["frequence_deplacement"] = data["frequence_deplacement"].map(
        {"Aucun": 0, "Occasionnel": 1, "Frequent": 2}
    )
    data = pd.get_dummies(
        data, columns=["statut_marital", "poste", "domaine_etude"], drop_first=True, dtype=int
    )
    X = pd.DataFrame(
        service.scaler.transform(data[service.features].astype(float)), columns=service.features
    )
    return service.model.predict_proba(X)[:, 1]


def test_api_matches_p4_on_full_dataset():
    service = get_prediction_service()
    fields = list(EmployeeInput.model_fields)
    df = _load_dataset()[fields]

    p_ref = _reference_probabilities(df, service)
    p_api = np.array(
        [
            service.model.predict_proba(
                preprocess_input(EmployeeInput(**row), service.features, service.scaler)
            )[0, 1]
            for row in df.to_dict("records")
        ]
    )

    np.testing.assert_allclose(p_api, p_ref, atol=1e-9)
    assert ((p_api >= service.threshold) == (p_ref >= service.threshold)).all()
