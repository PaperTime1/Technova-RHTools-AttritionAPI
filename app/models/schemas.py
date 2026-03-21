"""Schémas Pydantic pour la validation des données d'entrée et de sortie."""

from pydantic import BaseModel, Field
from datetime import datetime


class EmployeeInput(BaseModel):
    """Données d'un employé pour la prédiction d'attrition.

    Chaque champ correspond à une feature du modèle.
    Les contraintes (ge, le) valident les plages acceptables.
    """

    # ── SIRH ──
    age: int = Field(..., ge=18, le=70, description="Âge de l'employé")
    genre: str = Field(..., pattern="^(M|F)$", description="Genre (M ou F)")
    revenu_mensuel: float = Field(..., ge=0, description="Revenu mensuel en euros")
    statut_marital: str = Field(
        ..., pattern="^(Célibataire|Marié\\(e\\)|Divorcé\\(e\\))$",
        description="Statut marital"
    )
    poste: str = Field(..., description="Intitulé du poste")
    nombre_experiences_precedentes: int = Field(..., ge=0, description="Nombre d'employeurs précédents")
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
    domaine_etude: str = Field(..., description="Domaine d'études")
    frequence_deplacement: str = Field(
        ..., pattern="^(Aucun|Occasionnel|Frequent)$",
        description="Fréquence de déplacement"
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
    risk_level: str = Field(..., description="Niveau de risque (faible, modéré, élevé, critique)")
    threshold: float = Field(..., description="Seuil de décision utilisé")
    top_factors: list[dict] = Field(default_factory=list, description="Top facteurs de risque (SHAP)")


class PredictionLog(BaseModel):
    """Log d'une prédiction stockée en BDD."""

    id: int
    timestamp: datetime
    input_data: dict
    probability: float
    prediction: int
    risk_level: str


class HealthResponse(BaseModel):
    """Réponse du endpoint /health."""

    status: str = "ok"
    environment: str
    model_loaded: bool
    version: str = "0.1.0"
