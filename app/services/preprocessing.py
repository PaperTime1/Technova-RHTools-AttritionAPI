"""Preprocessing des données brutes pour le modèle de prédiction.

Reprend les fonctions engineer_features() et encode_features() du P4,
adaptées pour traiter une seule observation (via l'API).
"""

import numpy as np
import pandas as pd

from app.models.schemas import DOMAINES_ETUDE, POSTES, STATUTS_MARITAUX, EmployeeInput

# Modalités des variables nominales, dans l'ordre trié utilisé au P4
# (la première est la modalité de référence supprimée par drop_first).
NOMINAL_CATEGORIES: dict[str, list[str]] = {
    "statut_marital": sorted(STATUTS_MARITAUX),
    "poste": sorted(POSTES),
    "domaine_etude": sorted(DOMAINES_ETUDE),
}


def employee_to_dataframe(employee: EmployeeInput) -> pd.DataFrame:
    """Convertit un EmployeeInput Pydantic en DataFrame pandas (1 ligne)."""
    return pd.DataFrame([employee.model_dump()])


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Applique le feature engineering (identique au P4)."""
    data = df.copy()

    # Satisfaction moyenne
    cols_satisfaction = [
        "satisfaction_employee_environnement",
        "satisfaction_employee_nature_travail",
        "satisfaction_employee_equipe",
        "satisfaction_employee_equilibre_pro_perso",
    ]
    data["satisfaction_moyenne"] = data[cols_satisfaction].mean(axis=1)

    # Ratio fidélité
    data["anciennete_vs_experience"] = np.where(
        data["annee_experience_totale"] > 0,
        data["annees_dans_l_entreprise"] / data["annee_experience_totale"],
        0.0,
    )

    # Revenu par année d'XP
    data["revenu_par_annee_xp"] = np.where(
        data["annee_experience_totale"] > 0,
        data["revenu_mensuel"] / data["annee_experience_totale"],
        data["revenu_mensuel"],
    )

    return data


def encode_features(data: pd.DataFrame) -> pd.DataFrame:
    """Encode les variables catégorielles (identique au P4)."""
    encoded = data.copy()

    # Ordinales
    encoded["genre"] = encoded["genre"].map({"F": 0, "M": 1})
    encoded["heure_supplementaires"] = encoded["heure_supplementaires"].map({"Non": 0, "Oui": 1})
    encoded["frequence_deplacement"] = encoded["frequence_deplacement"].map(
        {"Aucun": 0, "Occasionnel": 1, "Frequent": 2}
    )

    # One-Hot Encoding à modalités FIXES.
    # pd.get_dummies ne connaît que les modalités présentes dans les lignes reçues :
    # sur une seule ligne avec drop_first=True, l'unique colonne créée était supprimée,
    # et toutes les indicatrices valaient 0 (training-serving skew). En déclarant les
    # modalités du P4 (triées, comme le fait get_dummies sur le dataset complet), on
    # obtient les mêmes colonnes quel que soit le nombre de lignes.
    for col, categories in NOMINAL_CATEGORIES.items():
        encoded[col] = pd.Categorical(encoded[col], categories=categories)
    encoded = pd.get_dummies(encoded, columns=list(NOMINAL_CATEGORIES), drop_first=True)

    # bool → int
    bool_cols = encoded.select_dtypes(include="bool").columns
    encoded[bool_cols] = encoded[bool_cols].astype(int)

    return encoded


def preprocess_input(employee: EmployeeInput, features: list[str], scaler) -> pd.DataFrame:
    """
    Pipeline complet : EmployeeInput → vecteur prêt pour le modèle.

    Paramètres
    ----------
    employee : EmployeeInput — données brutes de l'employé
    features : list[str] — liste ordonnée des features attendues par le modèle
    scaler : StandardScaler — scaler fitté sur le train set

    Retourne
    --------
    pd.DataFrame de shape (1, n_features) — vecteur scalé, colonnes nommées.
    Les noms permettent à scikit-learn de vérifier l'ordre des features.
    """
    # 1. Pydantic → DataFrame
    df = employee_to_dataframe(employee)

    # 2. Feature engineering
    df = engineer_features(df)

    # 3. Encoding
    df = encode_features(df)

    # 4. Garder les colonnes attendues, dans l'ordre du modèle.
    # Toutes doivent exister : une colonne manquante signale une incohérence entre
    # l'encodage et les artefacts, qu'on refuse au lieu de la combler silencieusement par 0.
    missing = [col for col in features if col not in df.columns]
    if missing:
        raise ValueError(f"Features attendues par le modèle absentes après encodage : {missing}")
    df = df[features]

    # 5. Scaling
    df_float = df.astype(float)
    scaled_array = scaler.transform(df_float)

    return pd.DataFrame(scaled_array, columns=features, index=df.index)
