"""Schémas Pydantic pour la validation des données d'entrée et de sortie."""

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

# Domaines des variables catégorielles (modalités observées dans le dataset du P4).
# Une valeur hors domaine est rejetée (422) au lieu d'être encodée silencieusement.
StatutMarital = Literal["Célibataire", "Divorcé(e)", "Marié(e)"]
Poste = Literal[
    "Assistant de Direction",
    "Cadre Commercial",
    "Consultant",
    "Directeur Technique",
    "Manager",
    "Représentant Commercial",
    "Ressources Humaines",
    "Senior Manager",
    "Tech Lead",
]
DomaineEtude = Literal[
    "Autre",
    "Entrepreunariat",
    "Infra & Cloud",
    "Marketing",
    "Ressources Humaines",
    "Transformation Digitale",
]

STATUTS_MARITAUX: tuple[str, ...] = get_args(StatutMarital)
POSTES: tuple[str, ...] = get_args(Poste)
DOMAINES_ETUDE: tuple[str, ...] = get_args(DomaineEtude)


class EmployeeInput(BaseModel):
    """Données d'un employé pour la prédiction d'attrition.

    Chaque champ correspond à une feature du modèle.
    Les contraintes (ge, le) valident les plages acceptables.
    """

    # ── SIRH ──
    age: int = Field(..., ge=18, le=70, description="Âge de l'employé")
    genre: str = Field(..., pattern="^(M|F)$", description="Genre (M ou F)")
    revenu_mensuel: float = Field(..., ge=0, description="Revenu mensuel en euros")
    statut_marital: StatutMarital = Field(..., description="Statut marital")
    poste: Poste = Field(..., description="Intitulé du poste")
    nombre_experiences_precedentes: int = Field(
        ..., ge=0, description="Nombre d'employeurs précédents"
    )
    annee_experience_totale: int = Field(..., ge=0, description="Années d'expérience totale")
    annees_dans_l_entreprise: int = Field(..., ge=0, description="Années chez TechNova")

    # ── Évaluations ──
    satisfaction_employee_environnement: int = Field(..., ge=1, le=4)
    note_evaluation_precedente: int = Field(..., ge=1, le=4)
    satisfaction_employee_nature_travail: int = Field(..., ge=1, le=4)
    satisfaction_employee_equipe: int = Field(..., ge=1, le=4)
    satisfaction_employee_equilibre_pro_perso: int = Field(..., ge=1, le=4)
    heure_supplementaires: str = Field(..., pattern="^(Oui|Non)$")
    augementation_salaire_precedente: float = Field(..., ge=0, le=50)

    # ── Sondage ──
    nombre_participation_pee: int = Field(..., ge=0)
    nb_formations_suivies: int = Field(..., ge=0)
    distance_domicile_travail: int = Field(..., ge=0)
    niveau_education: int = Field(..., ge=1, le=5)
    domaine_etude: DomaineEtude = Field(..., description="Domaine d'études")
    frequence_deplacement: str = Field(
        ..., pattern="^(Aucun|Occasionnel|Frequent)$", description="Fréquence de déplacement"
    )
    annees_depuis_la_derniere_promotion: int = Field(..., ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
            ]
        }
    }


class PredictionOutput(BaseModel):
    """Résultat de la prédiction d'attrition."""

    probability: float = Field(..., ge=0, le=1, description="Probabilité de départ (0-1)")
    prediction: int = Field(..., ge=0, le=1, description="Prédiction binaire (0=resté, 1=parti)")
    risk_level: Literal["faible", "modéré", "élevé", "critique"] = Field(
        ..., description="Niveau de risque ; « élevé » ou « critique » ⇔ prediction = 1"
    )
    threshold: float = Field(..., gt=0, lt=1, description="Seuil de décision utilisé")
    model_version: str = Field(..., description="Empreinte des artefacts du modèle servi")
    request_id: int | None = Field(None, description="Identifiant de la requête tracée en base")


class PredictionRecord(BaseModel):
    """Prédiction stockée en base."""

    model_config = ConfigDict(from_attributes=True)

    probability: float
    predicted_label: int
    risk_level: str
    threshold: float
    model_version: str


class PredictionLog(BaseModel):
    """Requête tracée en base, avec sa prédiction éventuelle."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    client_id: int | None
    employee_id: int | None
    status: str
    payload: dict
    error_detail: str | None
    latency_ms: float | None
    prediction: PredictionRecord | None


class HealthResponse(BaseModel):
    """Réponse du endpoint /health."""

    status: Literal["ok", "degraded"]
    environment: str
    model_loaded: bool
    database: Literal["ok", "unavailable"]
    model_version: str | None
    version: str
