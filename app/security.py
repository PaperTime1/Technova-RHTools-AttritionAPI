"""Authentification par clé d'API et contrôle d'accès par rôle.

- Les clés sont générées aléatoirement (256 bits, secrets.token_urlsafe(32)) : leur entropie
  est maximale, un hachage SHA-256 suffit donc pour les stocker. Un hachage lent et salé
  (Argon2, bcrypt) n'est utile que pour des secrets de faible entropie choisis par des humains.
- La base ne contient que l'empreinte : une fuite de la table ne révèle aucune clé utilisable.
- Clé absente ou invalide : 401 ; clé valide mais rôle insuffisant : 403.
"""

import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import ApiClient

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key", auto_error=False, description="Clé d'API fournie par l'administrateur"
)


def generate_api_key() -> str:
    """Génère une clé d'API aléatoire de 256 bits."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Empreinte SHA-256 (hexadécimale) d'une clé d'API."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "ApiKey"},
    )


def get_current_client(
    request: Request,
    api_key: str | None = Depends(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> ApiClient:
    """Identifie le client à partir de l'en-tête X-API-Key."""
    if not api_key:
        raise _unauthorized("Clé d'API manquante (en-tête X-API-Key)")

    client = db.scalar(select(ApiClient).where(ApiClient.key_hash == hash_api_key(api_key)))
    if client is None or client.revoked_at is not None:
        raise _unauthorized("Clé d'API invalide ou révoquée")

    request.state.client_id = client.id  # pour la traçabilité des requêtes rejetées
    return client


def require_admin(client: ApiClient = Depends(get_current_client)) -> ApiClient:
    """Réserve un endpoint aux clients de rôle 'admin'."""
    if client.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rôle 'admin' requis")
    return client
