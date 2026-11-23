"""Insertion du dataset complet (1 470 employés) dans la table employees.

Usage :
    python scripts/insert_dataset.py            # n'insère que si la table est vide (idempotent)
    python scripts/insert_dataset.py --replace  # vide la table puis réinsère

Ce script :
1. charge les 3 CSV sources (SIRH, évaluations, sondage) ;
2. les joint en un DataFrame central (jointure 1:1 vérifiée) ;
3. insère les lignes dans employees en UNE transaction (tout ou rien).

Non interactif : il peut être lancé automatiquement au déploiement (service init de Compose).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from sqlalchemy import delete, insert  # noqa: E402

from app.db.crud import get_employee_count  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.models.database import Employee  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_and_join(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Charge et joint les 3 fichiers sources (clé : identifiant employé)."""
    print("Chargement des fichiers sources...")

    sirh = pd.read_csv(data_dir / "extrait_sirh.csv")
    eval_ = pd.read_csv(data_dir / "extrait_eval.csv")
    sondage = pd.read_csv(data_dir / "extrait_sondage.csv")

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

    # Jointure 1:1 : validate lève une erreur si une clé est dupliquée
    df = sirh.merge(eval_, on="id_employee", how="inner", validate="one_to_one").merge(
        sondage, on="id_employee", how="inner", validate="one_to_one"
    )
    if len(df) != len(sirh):
        raise ValueError(f"Jointure incomplète : {len(df)} lignes pour {len(sirh)} employés")

    # Cible
    df["attrition"] = (df["a_quitte_l_entreprise"] == "Oui").astype(int)
    df = df.drop(columns=["a_quitte_l_entreprise"])

    print(f"  {df.shape[0]} employés, {df.shape[1]} colonnes")
    return df


def to_records(df: pd.DataFrame) -> list[dict]:
    """Prépare les lignes pour la table employees (id_employee devient la clé primaire)."""
    return df.rename(columns={"id_employee": "id"}).to_dict(orient="records")


def insert_employees(df: pd.DataFrame, replace: bool = False) -> int:
    """Insère les employés en une transaction. Retourne le nombre de lignes en base."""
    session = get_session_factory()()
    try:
        existing = get_employee_count(session)
        if existing and not replace:
            print(f"  Table employees déjà peuplée ({existing} lignes) : rien à faire.")
            return existing
        if existing:
            session.execute(delete(Employee))
        session.execute(insert(Employee), to_records(df))
        session.commit()
        count = get_employee_count(session)
        print(f"✓ {count} employés en base.")
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replace", action="store_true", help="vider la table avant insertion")
    args = parser.parse_args()
    insert_employees(load_and_join(), replace=args.replace)
