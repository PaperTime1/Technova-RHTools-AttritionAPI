"""Gestion de l'engine et des sessions SQLAlchemy.

Un seul engine (et donc un seul pool de connexions) par processus ; une session par
requête HTTP, validée en cas de succès et annulée en cas d'exception (atomicité).
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url_safe,
        pool_pre_ping=True,  # détecte les connexions coupées (base redémarrée)
        echo=False,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : une session par requête, une transaction par requête."""
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
