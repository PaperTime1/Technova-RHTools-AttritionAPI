"""Fixtures Pytest partagées pour tous les tests.

Base de test :
- TEST_DATABASE_URL défini (CI : service PostgreSQL 16) : on teste sur le même SGBD qu'en
  production (JSONB, contraintes CHECK, clés étrangères) ;
- sinon, SQLite local (rapide, mais un autre SGBD : à réserver au développement).
Chaque test démarre avec des tables vides.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.session import get_db
from app.main import app
from app.models.database import Base
from app.security import generate_api_key

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")
IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    test_engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(test_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # SQLite ignore les FK par défaut

else:
    test_engine = create_engine(
        TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    )

TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    """Même contrat que get_db (commit / rollback), sur la base de test."""
    db = TestSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Fixtures ──


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Crée le schéma au début de la session de tests."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Vide toutes les tables après chaque test (isolation)."""
    yield
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db_session():
    """Session de base de données pour un test individuel."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client():
    """Client FastAPI branché sur la base de test."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_client(name: str, role: str) -> str:
    key = generate_api_key()
    with TestSessionLocal() as db:
        crud.create_api_client(db, name, key, role)
        db.commit()
    return key


@pytest.fixture
def api_key() -> str:
    """Clé valide d'un client de rôle 'predict'."""
    return _make_client("test-predict", "predict")


@pytest.fixture
def admin_api_key() -> str:
    """Clé valide d'un client de rôle 'admin'."""
    return _make_client("test-admin", "admin")


@pytest.fixture
def sample_employee_data() -> dict:
    """Données d'un employé type pour les tests."""
    return {
        "age": 35,
        "genre": "M",
        "revenu_mensuel": 4500.0,
        "statut_marital": "Célibataire",
        "poste": "Consultant",
        "nombre_experiences_precedentes": 3,
        "annee_experience_totale": 8,
        "annees_dans_l_entreprise": 2,
        "satisfaction_employee_environnement": 2,
        "note_evaluation_precedente": 3,
        "satisfaction_employee_nature_travail": 3,
        "satisfaction_employee_equipe": 3,
        "satisfaction_employee_equilibre_pro_perso": 1,
        "heure_supplementaires": "Oui",
        "augementation_salaire_precedente": 12.0,
        "nombre_participation_pee": 0,
        "nb_formations_suivies": 2,
        "distance_domicile_travail": 15,
        "niveau_education": 3,
        "domaine_etude": "Infra & Cloud",
        "frequence_deplacement": "Frequent",
        "annees_depuis_la_derniere_promotion": 3,
    }


@pytest.fixture
def sample_low_risk_employee() -> dict:
    """Données d'un employé à faible risque (marié, pas d'heures sup, senior)."""
    return {
        "age": 45,
        "genre": "F",
        "revenu_mensuel": 12000.0,
        "statut_marital": "Marié(e)",
        "poste": "Senior Manager",
        "nombre_experiences_precedentes": 1,
        "annee_experience_totale": 20,
        "annees_dans_l_entreprise": 15,
        "satisfaction_employee_environnement": 4,
        "note_evaluation_precedente": 4,
        "satisfaction_employee_nature_travail": 4,
        "satisfaction_employee_equipe": 4,
        "satisfaction_employee_equilibre_pro_perso": 4,
        "heure_supplementaires": "Non",
        "augementation_salaire_precedente": 15.0,
        "nombre_participation_pee": 2,
        "nb_formations_suivies": 3,
        "distance_domicile_travail": 5,
        "niveau_education": 4,
        "domaine_etude": "Transformation Digitale",
        "frequence_deplacement": "Occasionnel",
        "annees_depuis_la_derniere_promotion": 1,
    }
