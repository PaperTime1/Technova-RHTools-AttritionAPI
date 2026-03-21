"""Preprocessing des données brutes pour le modèle de prédiction.

Reprend les fonctions engineer_features() et encode_features() du P4,
adaptées pour traiter une seule observation (via l'API).
"""

import numpy as np
import pandas as pd

from app.models.schemas import EmployeeInput


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

    # One-Hot Encoding
    cols_nominales = ["statut_marital", "poste", "domaine_etude"]
    encoded = pd.get_dummies(encoded, columns=cols_nominales, drop_first=True)

    # bool → int
    bool_cols = encoded.select_dtypes(include="bool").columns
    encoded[bool_cols] = encoded[bool_cols].astype(int)

    return encoded


def preprocess_input(employee: EmployeeInput, features: list[str], scaler) -> np.ndarray:
    """
    Pipeline complet : EmployeeInput → vecteur prêt pour le modèle.

    Paramètres
    ----------
    employee : EmployeeInput — données brutes de l'employé
    features : list[str] — liste ordonnée des features attendues par le modèle
    scaler : StandardScaler — scaler fitté sur le train set

    Retourne
    --------
    np.ndarray de shape (1, n_features) — vecteur scalé
    """
    # 1. Pydantic → DataFrame
    df = employee_to_dataframe(employee)

    # 2. Feature engineering
    df = engineer_features(df)

    # 3. Encoding
    df = encode_features(df)

    # 4. Aligner les colonnes avec celles du modèle
    # Les colonnes OHE manquantes (ex: poste_Manager si l'input est Consultant)
    # doivent être ajoutées à 0
    for col in features:
        if col not in df.columns:
            df[col] = 0

    # Ne garder que les colonnes attendues, dans le bon ordre
    df = df[features]

    # 5. Scaling
    # Identifier les colonnes non-binaires (même logique que le P4)
    cols_binaires = df.columns[df.iloc[0].isin([0, 1]) & (df.columns.str.contains("_") | df.columns.isin(["genre", "heure_supplementaires"]))]
    cols_a_scaler = [c for c in features if c not in cols_binaires or df[c].nunique() > 2]

    # Approche simplifiée : on scale toutes les colonnes comme le scaler a été fitté
    df_scaled = df.copy()
    df_scaled.iloc[:, :] = scaler.transform(df)

    return df_scaled.values
