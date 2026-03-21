"""Application FastAPI — API de prédiction d'attrition TechNova Partners."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import health, predict
from app.services.prediction import get_prediction_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle au démarrage, libère les ressources à l'arrêt."""
    # Startup : charger le modèle ML
    service = get_prediction_service()
    print(f"Modèle chargé ✓ ({len(service.features)} features, seuil={service.threshold:.3f})")
    yield
    # Shutdown : rien à libérer ici


settings = get_settings()

app = FastAPI(
    title="TechNova RHTools — Attrition API",
    description=(
        "API de prédiction du risque d'attrition des employés de TechNova Partners.\n\n"
        "**Modèle** : LogisticRegression (features sélectionnées)\n"
        "**Recall** : 85.1% | **Seuil** : 0.328 | **AUC-PR** : 0.600\n\n"
        "Chaque prédiction est loguée en base PostgreSQL pour la traçabilité."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enregistrement des routers
app.include_router(health.router)
app.include_router(predict.router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "TechNova Attrition API", "docs": "/docs"}
