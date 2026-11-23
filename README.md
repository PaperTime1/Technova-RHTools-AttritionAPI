# TechNova RHTools — Attrition API

API REST de prédiction du risque d'attrition des employés de **TechNova Partners** (ESN, conseil en transformation digitale et SaaS). Elle expose le modèle de classification construit au projet précédent (P4), trace chaque interaction en base PostgreSQL et est testée puis déployée automatiquement par GitHub Actions.

> Projet OpenClassrooms — parcours **AI Engineer**, projet 5 « Déployez un modèle de Machine Learning ».

## Sommaire

1. [Le modèle](#1-le-modèle)
2. [Architecture](#2-architecture)
3. [Installation](#3-installation)
4. [Utilisation de l'API](#4-utilisation-de-lapi)
5. [Authentification et sécurité](#5-authentification-et-sécurité)
6. [Données : stockage, traçabilité, gestion](#6-données--stockage-traçabilité-gestion)
7. [Besoins analytiques et suivi](#7-besoins-analytiques-et-suivi)
8. [Tests](#8-tests)
9. [CI/CD et environnements](#9-cicd-et-environnements)
10. [Déploiement](#10-déploiement)
11. [Maintenance et mise à jour du modèle](#11-maintenance-et-mise-à-jour-du-modèle)
12. [Conventions de développement](#12-conventions-de-développement)
13. [Choix techniques](#13-choix-techniques)

---

## 1. Le modèle

| Élément | Valeur |
|---|---|
| Problème | Classification binaire : l'employé va-t-il démissionner ? |
| Données | 1 470 employés (jointure 1:1 SIRH × évaluations × sondage), 237 départs (16,1 %) |
| Modèle | Régression logistique, `class_weight="balanced"`, 33 features (standardisées) |
| Seuil de décision | **0,328**, choisi par minimisation du coût métier (FN ≫ FP) en validation croisée |
| Rappel (test) | 0,851 — 40 départs détectés sur 47 |
| Précision (test) | 0,317 |
| AUC-PR (test) | 0,600 (référence aléatoire : 0,161) |

Le seuil n'est pas 0,5 car manquer un futur démissionnaire coûte bien plus cher qu'un entretien préventif inutile. Les probabilités renvoyées sont celles d'un modèle **pondéré** (`class_weight`) : elles servent à classer et à décider au seuil, pas à être lues comme des probabilités calibrées.

**Artefacts** (`artifacts/`) : modèle, scaler, liste ordonnée des features et seuil, sérialisés avec scikit-learn **1.6.1** (version épinglée dans `pyproject.toml` : un pickle n'est garanti qu'avec la version qui l'a produit). Au démarrage, l'API calcule l'empreinte SHA-256 de ces fichiers : c'est la **version du modèle** (`model_version`, par ex. `logreg-3f9a…`), renvoyée avec chaque prédiction et stockée en base.

**Cohérence entraînement / production.** Le preprocessing de l'API (`app/services/preprocessing.py`) reproduit celui du notebook P4. Le test `tests/test_non_regression.py` le vérifie sur **les 1 470 employés** : les probabilités servies sont identiques à celles du P4 (tolérance 1e-9).

## 2. Architecture

```
            ┌──────────────────────────── FastAPI (uvicorn) ───────────────────────────┐
 Client ──► │ X-API-Key ─► authentification (api_clients, empreinte SHA-256, rôles)    │
  HTTPS     │ JSON ──────► validation Pydantic (types, bornes, modalités) ─► 422      │
            │              preprocessing (identique P4) ─► modèle ─► seuil 0,328      │
            └───────────────────────────────┬──────────────────────────────────────────┘
                                            │ SQLAlchemy 2 (requêtes paramétrées), 1 transaction / requête
                                            ▼
                     PostgreSQL : employees · api_clients · prediction_requests · predictions
```

```
app/
├── main.py              Application, cycle de vie (chargement unique du modèle), traçabilité des 422
├── config.py            Configuration par variables d'environnement (pydantic-settings)
├── security.py          Clés d'API : génération, hachage, contrôle d'accès par rôle
├── models/schemas.py    Contrats d'entrée/sortie (Pydantic) → schéma OpenAPI
├── models/database.py   Modèle de données SQLAlchemy (tables, contraintes, index)
├── services/            preprocessing.py (features + encodage) · prediction.py (modèle, version)
├── routers/             predict.py (/predict…) · health.py (/health)
└── db/                  session.py (engine unique, session par requête) · crud.py
scripts/                 create_db.py · insert_dataset.py · create_api_client.py
tests/                   unitaires, intégration (PostgreSQL), fonctionnels, non-régression
docs/schema_bdd.md       Modèle de données détaillé (diagramme entité-association)
```

## 3. Installation

**Prérequis** : Python 3.11, [uv](https://docs.astral.sh/uv/), PostgreSQL 14+ (local ou Docker).

```bash
git clone https://github.com/PaperTime1/Technova-RHTools-AttritionAPI.git
cd Technova-RHTools-AttritionAPI

uv venv --python 3.11 && source .venv/bin/activate      # Windows : .venv\Scripts\activate
uv pip install -e ".[dev]"

cp .env.example .env                                     # puis renseigner DATABASE_URL

# PostgreSQL local avec Docker (optionnel)
docker run -d --name technova-pg -e POSTGRES_USER=technova -e POSTGRES_PASSWORD=<mdp> \
  -e POSTGRES_DB=technova_attrition -p 5432:5432 postgres:16

make db-create                                           # tables, contraintes, index
make db-insert                                           # 1 470 employés (idempotent)
make api-client NAME=moi ROLE=admin                      # affiche une clé d'API, une seule fois
make run                                                 # http://localhost:8000/docs
```

Avec Docker : `make docker-build && make docker-run` (l'image tourne sans privilèges root et expose un `HEALTHCHECK` sur `/health`).

## 4. Utilisation de l'API

La documentation interactive est générée depuis le code : **Swagger UI** sur `/docs`, ReDoc sur `/redoc` (schémas, exemples, codes d'erreur).

| Méthode | Endpoint | Description | Accès |
|---|---|---|---|
| `GET` | `/health` | État du modèle et de la base, version du modèle | public |
| `POST` | `/predict/` | Prédiction à partir d'un profil saisi (`?employee_id=` optionnel pour relier à un employé connu) | `predict`, `admin` |
| `POST` | `/predict/employees/{id}` | Prédiction pour un employé de la table `employees` | `predict`, `admin` |
| `GET` | `/predict/logs?limit=50` | Historique des requêtes et prédictions (1 ≤ limit ≤ 500) | `admin` |

```bash
curl -X POST http://localhost:8000/predict/ \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"age": 35, "genre": "M", "revenu_mensuel": 4500, "statut_marital": "Célibataire",
       "poste": "Consultant", "nombre_experiences_precedentes": 3, "annee_experience_totale": 8,
       "annees_dans_l_entreprise": 2, "satisfaction_employee_environnement": 2,
       "note_evaluation_precedente": 3, "satisfaction_employee_nature_travail": 3,
       "satisfaction_employee_equipe": 3, "satisfaction_employee_equilibre_pro_perso": 1,
       "heure_supplementaires": "Oui", "augementation_salaire_precedente": 12.0,
       "nombre_participation_pee": 0, "nb_formations_suivies": 2, "distance_domicile_travail": 15,
       "niveau_education": 3, "domaine_etude": "Infra & Cloud", "frequence_deplacement": "Frequent",
       "annees_depuis_la_derniere_promotion": 3}'

curl -X POST http://localhost:8000/predict/employees/42 -H "X-API-Key: $API_KEY"
```

Réponse :

```json
{
  "probability": 0.8123,
  "prediction": 1,
  "risk_level": "critique",
  "threshold": 0.3281563126252505,
  "model_version": "logreg-3f9a0c1d2e4b",
  "request_id": 128
}
```

Niveaux de risque : `faible` (< 0,15), `modéré` (< seuil), `élevé` (< 0,60), `critique`. « élevé » ou « critique » ⇔ `prediction = 1`.

**Codes de réponse.**

| Code | Cas |
|---|---|
| 200 | Prédiction effectuée |
| 401 | Clé absente, invalide ou révoquée |
| 403 | Rôle insuffisant (`/predict/logs` exige `admin`) |
| 404 | Employé inconnu |
| 422 | Entrée invalide : type, borne (âge 18–70, scores 1–4…) ou **modalité inconnue** (poste, domaine, statut) |
| 500 | Erreur interne de prédiction (tracée) |

## 5. Authentification et sécurité

**Authentification par clé d'API** (en-tête `X-API-Key`), adaptée à un usage de service à service (outil RH, tableau de bord).

- **Génération** : `scripts/create_api_client.py` crée une clé aléatoire de 256 bits (`secrets.token_urlsafe(32)`), l'affiche **une seule fois**, et n'en stocke que l'**empreinte SHA-256** (`api_clients.key_hash`). Une fuite de la base ne révèle donc aucune clé utilisable.
- **Pourquoi SHA-256 et pas bcrypt/Argon2** : une clé aléatoire de 256 bits est impossible à retrouver par recherche exhaustive. Les fonctions lentes et salées (Argon2id, bcrypt) servent aux secrets de **faible entropie** choisis par des humains, comme les mots de passe. Si l'API gérait des comptes utilisateurs avec mot de passe, ceux-ci seraient hachés avec Argon2id.
- **Gestion des accès** : chaque client a un **rôle** (`predict` : prédire ; `admin` : prédire et consulter l'historique, qui contient des données personnelles). Un client peut être **révoqué** (`revoked_at`) sans toucher aux autres.

**Bonnes pratiques appliquées.**

- **Secrets hors du code** : configuration par variables d'environnement (`.env` ignoré par Git, `.env.example` sans valeurs réelles) ; en production, `fly secrets set` ; en CI, GitHub Secrets **par environnement**. Aucune clé n'a de valeur par défaut.
- **Injection SQL** : impossible par construction, toutes les requêtes passent par l'ORM (requêtes paramétrées).
- **Validation stricte** des entrées par Pydantic : une valeur hors domaine est rejetée (422) au lieu d'être encodée silencieusement.
- **Moindre privilège** : en production, le rôle PostgreSQL de l'API n'a besoin que de `SELECT`/`INSERT` sur les 4 tables. La création du schéma est faite au déploiement par `release_command`.
- **Conteneur** sans root, HTTPS forcé (`force_https` Fly.io), erreurs 500 sans trace interne exposée.
- **Artefacts** : `joblib`/`pickle` peut exécuter du code au chargement ; seuls les artefacts versionnés de ce dépôt sont chargés.
- **RGPD** : les payloads contiennent des données personnelles RH (âge, salaire, genre, statut marital). L'accès à l'historique est réservé au rôle `admin` ; une durée de conservation des logs doit être fixée avec le DPO (purge des `prediction_requests` au-delà de N mois).

## 6. Données : stockage, traçabilité, gestion

Le modèle de données est détaillé dans [`docs/schema_bdd.md`](docs/schema_bdd.md) (diagramme entité-association, contraintes, index).

| Table | Contenu | Volume attendu |
|---|---|---|
| `employees` | Dataset de référence (1 470 employés, clé = identifiant SIRH d'origine) | stable |
| `api_clients` | Clients autorisés : nom, empreinte de clé, rôle, révocation | quelques lignes |
| `prediction_requests` | **Chaque requête** sur `/predict` : payload brut (JSONB), client, employé éventuel, statut (`success` / `rejected` / `error`), latence | croît avec l'usage |
| `predictions` | Sortie du modèle, **1:1** avec la requête : probabilité, décision, niveau, seuil, `model_version` | croît avec l'usage |

**Processus de traitement.**

1. **Initialisation** : `create_db.py` crée tables, clés étrangères, contraintes `CHECK` et index (idempotent) ; `insert_dataset.py` joint les 3 CSV (jointure **1:1 vérifiée** par `validate="one_to_one"`) et insère les 1 470 employés en **une transaction** (tout ou rien, idempotent, `--replace` pour réinsérer).
2. **À chaque appel** : requête et prédiction sont écrites dans **la même transaction** que la réponse. Les requêtes rejetées (422) et en erreur (500) sont aussi tracées : la traçabilité est complète, y compris pour les échecs.
3. **Intégrité** garantie par le SGBD, pas seulement par l'application : `CHECK` (probabilité ∈ [0,1], statut ∈ {success, rejected, error}, âge 18–70…), `UNIQUE` (une prédiction par requête, noms de clients), clés étrangères.
4. **Volume** : index sur `prediction_requests.created_at` (requêtes temporelles), `client_id` et `predictions.model_version`. Au-delà de quelques millions de lignes : partitionnement mensuel de `prediction_requests` et archivage.

## 7. Besoins analytiques et suivi

La table des requêtes alimente un **tableau de bord de suivi** (Metabase, Grafana ou requêtes SQL directes) :

| Indicateur | Pourquoi |
|---|---|
| Volume de requêtes par jour et par client | Usage, facturation interne, détection d'abus |
| Taux de rejets (422) et d'erreurs (500) | Qualité des intégrations clientes, incidents |
| Latence p50 / p95 | Performance du service |
| **Taux d'alerte** (part de `prediction = 1`) dans le temps | Premier symptôme d'un changement de population |
| Distribution des probabilités par semaine | Dérive du score |
| Dérive des features (PSI par variable vs dataset d'entraînement) | *Data drift* : PSI > 0,25 ⇒ réentraînement à envisager |
| Rappel et précision réels, une fois les départs connus | *Concept drift* : performance réelle du modèle |

```sql
-- Taux d'alerte et latence par semaine et par version du modèle
SELECT date_trunc('week', r.created_at) AS semaine, p.model_version,
       count(*) AS n, avg(p.predicted_label) AS taux_alerte,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY r.latency_ms) AS latence_p95_ms
FROM prediction_requests r JOIN predictions p ON p.request_id = r.id
GROUP BY 1, 2 ORDER BY 1;

-- Performance réelle : décisions du modèle vs issues observées (employés connus)
SELECT p.model_version, count(*) AS n,
       sum(CASE WHEN p.predicted_label = 1 AND e.attrition = 1 THEN 1 ELSE 0 END)::float
         / NULLIF(sum(e.attrition), 0) AS rappel
FROM predictions p
JOIN prediction_requests r ON r.id = p.request_id
JOIN employees e ON e.id = r.employee_id
GROUP BY 1;
```

## 8. Tests

```bash
make test                                                     # SQLite local (rapide)
TEST_DATABASE_URL=postgresql+psycopg://u:p@localhost:5432/test pytest   # PostgreSQL (comme la CI)
```

**90 tests**, **couverture 98 %** (lignes + branches, seuil bloquant de 85 % en CI). Rapport HTML dans `htmlcov/` (et en artefact de chaque exécution CI).

| Fichier | Type | Ce qui est vérifié |
|---|---|---|
| `test_preprocessing.py` | unitaire | Feature engineering, encodage (une seule ligne, indépendance au lot, modalité de référence), forme et absence de NaN |
| `test_prediction.py` | unitaire | Chargement, cohérence décision/seuil, niveaux de risque |
| `test_db.py` | intégration | CRUD, **intégrité** (CHECK, UNIQUE, FK, cascade), insertion des 1 470 employés et idempotence |
| `test_api.py` | fonctionnel | Endpoints, **401/403**, clé révoquée, clés jamais stockées en clair, **validation** (bornes, modalités inconnues), **traçabilité** des succès, rejets et erreurs |
| `test_infra.py` | intégration | Configuration, commit/rollback de la session, `/health` dégradé |
| `test_non_regression.py` | ML | L'API reproduit exactement le modèle P4 sur les 1 470 employés |

La couverture est un indicateur **nécessaire mais pas suffisant** : elle montre ce qui est exécuté, pas ce qui est vérifié. Les cas critiques (erreurs, frontières, cohérence avec le P4) sont donc testés explicitement. Le test de non-régression a été ajouté après la détection d'un décalage d'encodage entre entraînement et production ; il échoue sur l'ancienne version du code.

## 9. CI/CD et environnements

Workflow : [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

```
push / pull_request ──► lint (Ruff) ──► tests (PostgreSQL 16, couverture ≥ 85 %) ──► docker build
                                                                                       │
                       push sur develop ───────────────► deploy-staging    (environment: staging)
                       tag vX.Y.Z ─────────────────────► deploy-production (environment: production)
                                                          └─► smoke test GET /health
```

| Environnement | Déclencheur | Base | Secrets |
|---|---|---|---|
| `development` | poste local | PostgreSQL local / SQLite (tests) | `.env` (non versionné) |
| `test` | chaque push et PR | PostgreSQL 16 éphémère (service CI) | aucun secret requis |
| `staging` | push sur `develop` | base Fly.io de staging | GitHub Environment `staging` : `FLY_API_TOKEN`, variable `FLY_APP` |
| `production` | tag `vX.Y.Z` | base Fly.io de production | GitHub Environment `production` (approbation manuelle possible) |

- **Validation avant fusion** : la protection de branche sur `main` et `develop` exige que `lint` et `test` soient verts.
- **Secrets** : stockés chiffrés dans les GitHub Environments, injectés en variables d'environnement, masqués dans les logs, jamais transmis aux workflows de forks.
- `concurrency` annule les exécutions obsolètes ; le cache uv garde le pipeline sous quelques minutes.

## 10. Déploiement

**Local** (accepté par l'énoncé depuis septembre 2026) : section [Installation](#3-installation), ou l'image Docker.

**Fly.io** (production) :

```bash
fly launch --no-deploy                          # première fois
fly postgres create && fly postgres attach <db> # fournit DATABASE_URL en secret
fly deploy                                      # ou via la CI (tag vX.Y.Z)
fly ssh console -C "python scripts/create_api_client.py --name rh-dashboard"
```

À chaque déploiement, `release_command` (`fly.toml`) crée les tables manquantes et insère le dataset si nécessaire **avant** la mise en service ; en cas d'échec, l'ancienne version reste en ligne. Le *health check* Fly.io interroge `/health`. **Retour arrière** : redéployer le tag précédent (`git checkout v1.0.0 && fly deploy`).

## 11. Maintenance et mise à jour du modèle

1. **Déclencheurs** : réentraînement trimestriel, ou alerte de suivi (PSI > 0,25 sur une feature importante, taux d'alerte hors de [10 %, 50 %], baisse du rappel observé).
2. **Réentraînement** sur les données récentes (notebook P4 rejoué), même protocole : validation croisée stratifiée, seuil choisi sur les prédictions hors-fold.
3. **Validation champion / challenger** hors ligne sur le même jeu de test ; promotion seulement si le coût métier baisse sans dégrader le rappel.
4. **Livraison** : nouveaux artefacts dans `artifacts/`, mise à jour de la référence de non-régression, version **MINEURE** (`v1.1.0`) si le contrat d'API est inchangé, **MAJEURE** sinon. La `model_version` change automatiquement (empreinte des artefacts).
5. **Déploiement** : staging, vérification, tag, production ; suivi rapproché du taux d'alerte les premières semaines.

## 12. Conventions de développement

- **Branches** : `main` (production, protégée), `develop` (intégration → staging), `feature/<sujet>` et `fix/<sujet>` fusionnées par pull request avec CI verte.
- **Commits** : *Conventional Commits* (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `refactor:`).
- **Versions** : *Semantic Versioning* via des tags annotés `vMAJEUR.MINEUR.CORRECTIF`. MAJEUR = contrat d'API cassé (`v1.0.0` : authentification par clients et nouveau format de réponse).
- **Code** : Ruff (lint + format, 100 colonnes), annotations de type, docstrings en français.
- **ML** : un changement de preprocessing ou d'artefact doit garder `test_non_regression.py` vert (ou mettre à jour la référence dans la même PR, avec justification).

## 13. Choix techniques

| Composant | Choix | Justification |
|---|---|---|
| API | FastAPI | Validation Pydantic, documentation OpenAPI générée du code, injection de dépendances testable |
| Routes | synchrones (`def`) | scikit-learn et psycopg sont bloquants : FastAPI les exécute dans un pool de threads |
| Modèle | chargé une fois (`lifespan`) | Pas de rechargement disque à chaque requête |
| Base | PostgreSQL 16 | Transactions ACID, contraintes, JSONB pour les payloads bruts |
| ORM | SQLAlchemy 2 | Requêtes paramétrées, un pool de connexions par processus, schéma déclaratif |
| Authentification | Clés d'API hachées + rôles | Adapté au service à service, révocable, aucun secret en clair en base |
| Tests | Pytest, PostgreSQL en CI | On teste sur le SGBD de production |
| CI/CD | GitHub Actions + Environments | Environnements et secrets natifs, approbation de production |
| Hébergement | Fly.io | Docker, PostgreSQL managé, `release_command` pour initialiser la base |

---

*Projet réalisé dans le cadre du parcours AI Engineer — OpenClassrooms.*
