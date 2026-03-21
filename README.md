# TechNova RHTools — Attrition API

API de prédiction du risque d'attrition des employés de **TechNova Partners**, une ESN spécialisée en transformation digitale et SaaS.

## Contexte

TechNova fait face à un taux d'attrition de 16.1%. Ce projet expose un modèle de Machine Learning via une API REST pour :
- **Scorer** chaque employé avec une probabilité de départ
- **Identifier** le niveau de risque (faible, modéré, élevé, critique)
- **Tracer** chaque prédiction en base PostgreSQL

**Modèle** : LogisticRegression | **Recall** : 85.1% | **AUC-PR** : 0.600 | **Seuil** : 0.328

## Architecture

```
Client → FastAPI (+ Pydantic validation) → Modèle ML (scikit-learn)
                     ↓
              PostgreSQL (logs des prédictions)
```

## Installation

### Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de packages)
- PostgreSQL 14+ (local ou Docker)

### Installation locale

```bash
# Cloner le repo
git clone https://github.com/<votre-user>/Technova-RHTools-AttritionAPI.git
cd Technova-RHTools-AttritionAPI

# Installer les dépendances
uv pip install --system ".[dev]"

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos paramètres PostgreSQL

# Créer la base de données
make db-create

# Insérer le dataset
make db-insert

# Lancer l'API
make run
```

L'API est accessible sur `http://localhost:8000`. La documentation Swagger est sur `http://localhost:8000/docs`.

### Docker

```bash
docker build -t technova-attrition-api .
docker run -p 8000:8000 --env-file .env technova-attrition-api
```

## Utilisation de l'API

### Authentification

Toutes les requêtes vers `/predict/` nécessitent un header `X-API-Key` :

```bash
curl -X POST http://localhost:8000/predict/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre-clé-api" \
  -d '{
    "age": 35,
    "genre": "M",
    "revenu_mensuel": 4500,
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
    "annees_depuis_la_derniere_promotion": 3
  }'
```

### Réponse

```json
{
  "probability": 0.7234,
  "prediction": 1,
  "risk_level": "élevé",
  "threshold": 0.328,
  "top_factors": []
}
```

### Endpoints

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/health` | État de l'API et du modèle | Non |
| `POST` | `/predict/` | Prédiction d'attrition | `X-API-Key` |
| `GET` | `/predict/logs` | Historique des prédictions | `X-API-Key` |
| `GET` | `/docs` | Documentation Swagger | Non |
| `GET` | `/redoc` | Documentation ReDoc | Non |

## Tests

```bash
# Lancer tous les tests avec couverture
make test

# Ou directement
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Le rapport de couverture HTML est généré dans `htmlcov/`.

## Déploiement

### Fly.io

```bash
# Installer le CLI Fly
curl -L https://fly.io/install.sh | sh

# Se connecter
flyctl auth login

# Créer l'app (première fois)
flyctl launch

# Créer la base PostgreSQL
flyctl postgres create

# Configurer les secrets
flyctl secrets set DATABASE_URL="postgres://..." API_KEY="votre-clé" SECRET_KEY="votre-secret"

# Déployer
flyctl deploy
```

### CI/CD (GitHub Actions)

Le pipeline automatisé (`.github/workflows/ci.yml`) exécute :

1. **Lint** — Vérification du code avec Ruff
2. **Tests** — Pytest avec PostgreSQL en service (couverture)
3. **Deploy** — Déploiement automatique sur Fly.io (branche `main` uniquement)

Les secrets sont gérés via GitHub Secrets : `FLY_API_TOKEN`.

## Structure du projet

```
├── app/
│   ├── main.py              # Application FastAPI
│   ├── config.py            # Settings (variables d'env)
│   ├── models/
│   │   ├── schemas.py       # Schémas Pydantic (I/O)
│   │   └── database.py      # Modèles SQLAlchemy
│   ├── services/
│   │   ├── prediction.py    # Service de prédiction ML
│   │   └── preprocessing.py # Pipeline de preprocessing
│   ├── routers/
│   │   ├── predict.py       # Endpoints /predict
│   │   └── health.py        # Endpoint /health
│   └── db/
│       ├── session.py       # Session SQLAlchemy
│       └── crud.py          # Opérations CRUD
├── artifacts/               # Modèle et scaler sérialisés
├── scripts/                 # Scripts de gestion BDD
├── tests/                   # Tests Pytest
├── docs/                    # Documentation technique
├── .github/workflows/       # CI/CD
├── Dockerfile
├── fly.toml                 # Config Fly.io
└── pyproject.toml           # Dépendances
```

## Choix techniques

| Composant | Choix | Justification |
|-----------|-------|---------------|
| Framework API | FastAPI | Async, validation Pydantic intégrée, docs auto |
| Base de données | PostgreSQL | Robuste, type JSON natif pour les logs |
| ORM | SQLAlchemy 2.0 | Standard Python, support PostgreSQL complet |
| ML | scikit-learn (LogReg) | Meilleur compromis recall/overfit sur ce dataset |
| Déploiement | Fly.io | PostgreSQL intégré, tier gratuit, déploiement Docker |
| CI/CD | GitHub Actions | Intégré à GitHub, PostgreSQL en service de test |
| Tests | Pytest + pytest-cov | Standard Python, couverture mesurée |

## Performances du modèle

| Métrique | Valeur |
|----------|--------|
| Recall | 85.1% (40/47 départs détectés) |
| Precision | 31.7% |
| AUC-PR | 0.600 |
| Coût métier | 685 250€ (vs 2.17M€ sans modèle) |
| Seuil de décision | 0.328 (optimisé par coût métier) |

## Licence

Projet réalisé dans le cadre du parcours Data Scientist — OpenClassrooms.
