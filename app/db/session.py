"""Gestion de la session SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import get_settings


def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, echo=(settings.environment == "development"))


def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI : fournit une session DB par requête."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
