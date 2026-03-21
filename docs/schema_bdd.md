# Schéma de la base de données

## Vue d'ensemble

La base PostgreSQL `technova_attrition` contient deux tables :

```
┌─────────────────────────────┐       ┌──────────────────────────────┐
│        employees            │       │      prediction_logs         │
├─────────────────────────────┤       ├──────────────────────────────┤
│ id              SERIAL PK   │       │ id              SERIAL PK    │
│ age             INTEGER      │       │ timestamp       TIMESTAMPTZ  │
│ genre           VARCHAR(1)   │       │ input_data      JSON         │
│ revenu_mensuel  FLOAT        │       │ probability     FLOAT        │
│ statut_marital  VARCHAR(50)  │       │ prediction      INTEGER      │
│ poste           VARCHAR(100) │       │ risk_level      VARCHAR(20)  │
│ departement     VARCHAR(100) │       │ threshold_used  FLOAT        │
│ ...22 autres colonnes        │       └──────────────────────────────┘
│ attrition       INTEGER      │
└─────────────────────────────┘
```

## Table `employees`

Contient le dataset complet (1 470 employés) issu de la jointure des 3 fichiers sources.
Sert de référence pour les analyses et l'alimentation du modèle.

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | SERIAL | PK | Identifiant auto-incrémenté |
| `age` | INTEGER | NOT NULL | Âge de l'employé |
| `genre` | VARCHAR(1) | NOT NULL | M ou F |
| `revenu_mensuel` | FLOAT | NOT NULL | Revenu mensuel en euros |
| `statut_marital` | VARCHAR(50) | NOT NULL | Célibataire, Marié(e), Divorcé(e) |
| `poste` | VARCHAR(100) | NOT NULL | Intitulé du poste |
| `departement` | VARCHAR(100) | | Département (Commercial, Consulting, RH) |
| `nombre_experiences_precedentes` | INTEGER | | Nombre d'employeurs précédents |
| `annee_experience_totale` | INTEGER | | Années d'expérience totale |
| `annees_dans_l_entreprise` | INTEGER | | Ancienneté chez TechNova |
| `heure_supplementaires` | VARCHAR(3) | | Oui / Non |
| `satisfaction_employee_*` | INTEGER | | Scores de satisfaction (1-4) |
| `note_evaluation_precedente` | INTEGER | | Note d'évaluation (1-4) |
| `augementation_salaire_precedente` | FLOAT | | % d'augmentation précédente |
| `nombre_participation_pee` | INTEGER | | Participations au PEE |
| `nb_formations_suivies` | INTEGER | | Formations suivies |
| `distance_domicile_travail` | INTEGER | | Distance en km |
| `niveau_education` | INTEGER | | Niveau (1-5) |
| `domaine_etude` | VARCHAR(100) | | Domaine d'études |
| `frequence_deplacement` | VARCHAR(50) | | Aucun, Occasionnel, Frequent |
| `annees_depuis_la_derniere_promotion` | INTEGER | | Années sans promotion |
| `attrition` | INTEGER | | 0 = resté, 1 = parti |

## Table `prediction_logs`

Enregistre chaque appel à l'endpoint `/predict/` pour assurer la traçabilité complète
des interactions avec le modèle ML.

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | SERIAL | PK | Identifiant auto-incrémenté |
| `timestamp` | TIMESTAMPTZ | NOT NULL | Date/heure de la prédiction |
| `input_data` | JSON | NOT NULL | Données brutes envoyées à l'API |
| `probability` | FLOAT | NOT NULL | Probabilité de départ (0-1) |
| `prediction` | INTEGER | NOT NULL | 0 = resté, 1 = parti |
| `risk_level` | VARCHAR(20) | NOT NULL | faible, modéré, élevé, critique |
| `threshold_used` | FLOAT | NOT NULL | Seuil de décision utilisé |
