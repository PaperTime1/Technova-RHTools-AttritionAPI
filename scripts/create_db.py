"""Script de création de la base de données et des tables.

Usage :
    python scripts/create_db.py

Ce script crée toutes les tables définies dans app/models/database.py
dans la base PostgreSQL configurée via DATABASE_URL.
"""

import sys
from pathlib import Path

# Ajouter la racine du projet au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect

from app.db.session import get_engine
from app.models.database import Base


def create_database():
    """Crée toutes les tables dans la base PostgreSQL."""
    engine = get_engine()

    print(f"Connexion : {engine.url}")
    print("Création des tables...")

    Base.metadata.create_all(bind=engine)

    # Vérification
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables créées ({len(tables)}) :")
    for table in tables:
        cols = inspector.get_columns(table)
        print(f"  ✓ {table} ({len(cols)} colonnes)")
        for col in cols:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"      {col['name']:<45} {str(col['type']):<20} {nullable}")

    print("\nBase de données prête ✓")


if __name__ == "__main__":
    create_database()
