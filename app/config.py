"""Configuration de l'application via variables d'environnement (12-factor, facteur III)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application, chargés depuis .env ou les variables d'environnement.

    Aucun secret n'a de valeur par défaut : les clés d'API sont stockées hachées en base
    (table api_clients) et créées avec scripts/create_api_client.py.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de données
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/technova_attrition"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: Literal["development", "test", "staging", "production"] = "development"

    # Chemins des artefacts ML
    model_path: str = "artifacts/modele_final.joblib"
    scaler_path: str = "artifacts/scaler_sel.joblib"
    features_path: str = "artifacts/features_finales.joblib"
    threshold_path: str = "artifacts/seuil_final.joblib"

    @property
    def database_url_safe(self) -> str:
        """Normalise l'URL pour SQLAlchemy (Fly.io fournit postgres://)."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Singleton pour les settings (chargés une seule fois)."""
    return Settings()
