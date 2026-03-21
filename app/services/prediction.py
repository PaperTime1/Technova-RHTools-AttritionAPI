"""Service de prédiction d'attrition.

Charge les artefacts ML et expose la logique de prédiction.
"""

import joblib

from app.config import get_settings
from app.models.schemas import EmployeeInput, PredictionOutput
from app.services.preprocessing import preprocess_input


class PredictionService:
    """Service singleton qui charge le modèle et effectue les prédictions."""

    def __init__(self):
        settings = get_settings()
        self.model = joblib.load(settings.model_path)
        self.scaler = joblib.load(settings.scaler_path)
        self.features: list[str] = joblib.load(settings.features_path)
        self.threshold: float = joblib.load(settings.threshold_path)
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, employee: EmployeeInput) -> PredictionOutput:
        """
        Prédit la probabilité d'attrition d'un employé.

        Paramètres
        ----------
        employee : EmployeeInput — données validées par Pydantic

        Retourne
        --------
        PredictionOutput avec probabilité, prédiction binaire et niveau de risque
        """
        # Preprocessing
        X = preprocess_input(employee, self.features, self.scaler)

        # Prédiction
        probability = float(self.model.predict_proba(X)[0, 1])
        prediction = int(probability >= self.threshold)

        # Niveau de risque
        risk_level = self._compute_risk_level(probability)

        return PredictionOutput(
            probability=round(probability, 4),
            prediction=prediction,
            risk_level=risk_level,
            threshold=self.threshold,
            top_factors=[],  # SHAP sera ajouté plus tard si besoin
        )

    @staticmethod
    def _compute_risk_level(probability: float) -> str:
        """Traduit la probabilité en niveau de risque lisible par les RH."""
        if probability < 0.15:
            return "faible"
        elif probability < 0.33:
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
