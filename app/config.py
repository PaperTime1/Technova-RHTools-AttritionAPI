"""Configuration de l'application via variables d'environnement."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Paramètres de l'application, chargés depuis .env ou les variables d'environnement."""

    # Base de données
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/technova_attrition"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"

    # Sécurité
    secret_key: str = "change-me-in-production"
    api_key: str = "technova-dev-key-2025"

    # Chemins des artefacts ML
    model_path: str = "artifacts/modele_final.joblib"
    scaler_path: str = "artifacts/scaler_sel.joblib"
    features_path: str = "artifacts/features_finales.joblib"
    threshold_path: str = "artifacts/seuil_final.joblib"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Singleton pour les settings (chargés une seule fois)."""
    return Settings()
