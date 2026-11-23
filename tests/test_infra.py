"""Tests de l'infrastructure : configuration, sessions de base, endpoint de santé dégradé."""

import pytest
from sqlalchemy import select

from app.config import Settings
from app.db import session as session_module
from app.models.database import ApiClient
from tests.conftest import TestSessionLocal


class TestConfig:
    @pytest.mark.parametrize(
        ("url", "expected_prefix"),
        [
            ("postgres://u:p@h:5432/db", "postgresql+psycopg://"),
            ("postgresql://u:p@h:5432/db", "postgresql+psycopg://"),
            ("postgresql+psycopg://u:p@h:5432/db", "postgresql+psycopg://"),
        ],
    )
    def test_database_url_normalized(self, url, expected_prefix):
        """Une URL postgres:// (fournie par certains hébergeurs) est convertie pour psycopg 3."""
        assert Settings(database_url=url).database_url_safe.startswith(expected_prefix)

    def test_invalid_environment_rejected(self):
        with pytest.raises(ValueError):
            Settings(environment="prod-typo")


class TestGetDb:
    """La dépendance get_db valide la transaction en cas de succès, l'annule sinon."""

    @pytest.fixture(autouse=True)
    def _use_test_factory(self, monkeypatch):
        monkeypatch.setattr(session_module, "get_session_factory", lambda: TestSessionLocal)

    def test_commit_on_success(self):
        gen = session_module.get_db()
        db = next(gen)
        db.add(ApiClient(name="commit", key_hash="a" * 64, role="predict"))
        with pytest.raises(StopIteration):
            next(gen)
        with TestSessionLocal() as check:
            assert check.scalar(select(ApiClient).where(ApiClient.name == "commit")) is not None

    def test_rollback_on_exception(self):
        gen = session_module.get_db()
        db = next(gen)
        db.add(ApiClient(name="rollback", key_hash="b" * 64, role="predict"))
        db.flush()
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("échec dans la route"))
        with TestSessionLocal() as check:
            assert check.scalar(select(ApiClient).where(ApiClient.name == "rollback")) is None


class TestHealthDegraded:
    def test_database_unavailable(self, client, monkeypatch):
        from app.db.session import get_db
        from app.main import app

        class BrokenSession:
            def execute(self, *_args, **_kwargs):
                raise ConnectionError("base injoignable")

        app.dependency_overrides[get_db] = lambda: BrokenSession()
        data = client.get("/health").json()
        assert data["status"] == "degraded"
        assert data["database"] == "unavailable"
        assert data["model_loaded"] is True

    def test_model_unavailable(self, client, monkeypatch):
        import app.routers.health as health

        def broken_service():
            raise FileNotFoundError("artefact manquant")

        monkeypatch.setattr(health, "get_prediction_service", broken_service)
        data = client.get("/health").json()
        assert data["status"] == "degraded"
        assert data["model_loaded"] is False
        assert data["model_version"] is None
