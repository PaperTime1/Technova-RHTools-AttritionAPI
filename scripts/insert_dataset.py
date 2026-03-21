"""Script d'insertion du dataset complet dans PostgreSQL.

Usage :
    python scripts/insert_dataset.py

Ce script :
1. Charge les 3 CSV sources (SIRH, évaluations, sondage)
2. Les joint en un DataFrame central
3. Insère les données dans la table 'employees'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.database import Employee
from app.db.session import get_engine, get_session_factory


DATA_DIR = Path("data")


def load_and_join() -> pd.DataFrame:
    """Charge et joint les 3 fichiers sources."""
    print("Chargement des fichiers sources...")

    sirh = pd.read_csv(DATA_DIR / "extrait_sirh.csv")
    eval_ = pd.read_csv(DATA_DIR / "extrait_eval.csv")
    sondage = pd.read_csv(DATA_DIR / "extrait_sondage.csv")

    # Harmonisation des clés
    eval_["id_employee"] = eval_["eval_number"].str.replace("E_", "", regex=False).astype(int)
    sondage = sondage.rename(columns={"code_sondage": "id_employee"})

    # Nettoyage
    sirh = sirh.drop(columns=["nombre_heures_travailless"])
    sondage = sondage.drop(columns=["ayant_enfants", "nombre_employee_sous_responsabilite"])
    eval_["augementation_salaire_precedente"] = (
        eval_["augementation_salaire_precedente"].str.replace(" %", "", regex=False).astype(float)
    )
    eval_ = eval_.drop(columns=["eval_number"])

    # Jointure
    df = sirh.merge(eval_, on="id_employee", how="inner").merge(sondage, on="id_employee", how="inner")

    # Target
    df["attrition"] = (df["a_quitte_l_entreprise"] == "Oui").astype(int)
    df = df.drop(columns=["a_quitte_l_entreprise", "id_employee"])

    print(f"  {df.shape[0]} employés, {df.shape[1]} colonnes")
    return df


def insert_employees(df: pd.DataFrame):
    """Insère les employés dans la table PostgreSQL."""
    engine = get_engine()
    SessionLocal = get_session_factory()
    session = SessionLocal()

    try:
        # Vérifier si la table est déjà peuplée
        existing = session.query(Employee).count()
        if existing > 0:
            print(f"  Table employees contient déjà {existing} lignes.")
            response = input("  Supprimer et réinsérer ? (o/N) : ")
            if response.lower() != "o":
                print("  Insertion annulée.")
                return
            session.query(Employee).delete()
            session.commit()

        # Insertion
        print(f"Insertion de {len(df)} employés...")
        records = df.to_dict(orient="records")

        for i, record in enumerate(records):
            employee = Employee(**record)
            session.add(employee)

            if (i + 1) % 200 == 0:
                session.commit()
                print(f"  {i + 1}/{len(records)} insérés...")

        session.commit()
        final_count = session.query(Employee).count()
        print(f"\n✓ {final_count} employés insérés en base.")

    except Exception as e:
        session.rollback()
        print(f"✗ Erreur : {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    df = load_and_join()
    insert_employees(df)
