"""Application FastAPI — API de prédiction d'attrition TechNova Partners."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

from app import __version__
from app.db import crud
from app.db.session import get_db
from app.routers import health, predict
from app.services.prediction import get_prediction_service

logger = logging.getLogger("technova.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle une seule fois au démarrage."""
    service = get_prediction_service()
    logger.info(
        "Modèle chargé : %s (%d features, seuil=%.3f)",
        service.model_version,
        len(service.features),
        service.threshold,
    )
    yield


app = FastAPI(
    title="TechNova RHTools — Attrition API",
    description=(
        "API de prédiction du risque d'attrition des employés de TechNova Partners.\n\n"
        "**Modèle** : régression logistique (`class_weight=balanced`), 33 features.\n"
        "**Seuil métier** : 0,328 (minimisation du coût FN/FP en validation croisée).\n"
        "**Performances (test)** : rappel 0,851 · précision 0,317 · AUC-PR 0,600.\n\n"
        "**Authentification** : en-tête `X-API-Key` (rôles `predict` et `admin`).\n\n"
        "Chaque requête sur `/predict` — réussie, rejetée ou en erreur — est tracée en base "
        "PostgreSQL avec la version du modèle."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health.router)
app.include_router(predict.router)


@app.exception_handler(RequestValidationError)
async def log_rejected_requests(request: Request, exc: RequestValidationError):
    """Trace en base les requêtes /predict rejetées par la validation, puis répond 422."""
    if request.method == "POST" and request.url.path.startswith("/predict"):
        body = exc.body if isinstance(exc.body, dict) else {"raw": str(exc.body)}
        # Respecte les surcharges de dépendances (base de test) : même session que les routes
        db_dependency = app.dependency_overrides.get(get_db, get_db)
        sessions = db_dependency()
        db = next(sessions)
        try:
            crud.create_request(
                db,
                jsonable_encoder(body),
                "rejected",
                client_id=getattr(request.state, "client_id", None),
                error_detail=str(jsonable_encoder(exc.errors()))[:2000],
            )
            db.commit()
        except Exception:  # la traçabilité ne doit jamais masquer la réponse 422
            db.rollback()
            logger.exception("Échec de la traçabilité d'une requête rejetée")
        finally:
            sessions.close()
    return await request_validation_exception_handler(request, exc)


@app.get("/", include_in_schema=False)
def root():
    return {"message": "TechNova Attrition API", "docs": "/docs", "version": __version__}
