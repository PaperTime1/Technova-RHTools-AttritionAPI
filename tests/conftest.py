"""Fixtures Pytest partagées pour tous les tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.database import Base

# ── BDD de test en mémoire (SQLite) ──
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    """Remplace la session PostgreSQL par SQLite pour les tests."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Fixtures ──


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Crée les tables au début de la session de tests."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


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
    """Client FastAPI pour les tests d'endpoints."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_key():
    """Clé API valide pour les tests."""
    settings = get_settings()
    return settings.api_key


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
