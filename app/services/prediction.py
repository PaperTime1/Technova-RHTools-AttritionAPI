"""Service de prédiction d'attrition.

Charge les artefacts ML une seule fois et expose la logique de prédiction.
"""

import hashlib
from pathlib import Path

import joblib

from app.config import get_settings
from app.models.schemas import EmployeeInput, PredictionOutput
from app.services.preprocessing import preprocess_input


def _artifacts_fingerprint(paths: list[str]) -> str:
    """Empreinte SHA-256 de l'ensemble des artefacts : identifie la version du modèle servi."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(Path(path).read_bytes())
    return digest.hexdigest()[:12]


class PredictionService:
    """Service singleton qui charge le modèle et effectue les prédictions."""

    def __init__(self):
        settings = get_settings()
        paths = [
            settings.model_path,
            settings.scaler_path,
            settings.features_path,
            settings.threshold_path,
        ]
        self.model = joblib.load(settings.model_path)
        self.scaler = joblib.load(settings.scaler_path)
        self.features: list[str] = joblib.load(settings.features_path)
        self.threshold: float = float(joblib.load(settings.threshold_path))
        # Version tracée en base avec chaque prédiction (traçabilité modèle ↔ décision)
        self.model_version = f"logreg-{_artifacts_fingerprint(paths)}"
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, employee: EmployeeInput) -> PredictionOutput:
        """Prédit la probabilité d'attrition d'un employé."""
        X = preprocess_input(employee, self.features, self.scaler)

        probability = float(self.model.predict_proba(X)[0, 1])
        prediction = int(probability >= self.threshold)

        return PredictionOutput(
            probability=round(probability, 4),
            prediction=prediction,
            risk_level=self._compute_risk_level(probability, self.threshold),
            threshold=self.threshold,
            model_version=self.model_version,
        )

    @staticmethod
    def _compute_risk_level(probability: float, threshold: float = 0.328) -> str:
        """Traduit la probabilité en niveau de risque lisible par les RH.

        La frontière modéré/élevé est le seuil de décision : « élevé » ou « critique »
        si et seulement si le modèle prédit un départ (prediction = 1).
        """
        if probability < 0.15:
            return "faible"
        elif probability < threshold:
            return "modéré"
        elif probability < 0.60:
            return "élevé"
        else:
            return "critique"


# Singleton global
_service: PredictionService | None = None


def get_prediction_service() -> PredictionService:
    """Retourne le service de prédiction (initialisé au premier appel)."""
    global _service
    if _service is None:
        _service = PredictionService()
    return _service
