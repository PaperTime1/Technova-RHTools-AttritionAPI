"""Création d'un client de l'API et de sa clé.

Usage :
    python scripts/create_api_client.py --name rh-dashboard
    python scripts/create_api_client.py --name admin --role admin

La clé est générée aléatoirement (256 bits) et affichée UNE SEULE FOIS : seule son
empreinte SHA-256 est stockée en base. En cas de perte, on révoque le client et on en crée
un nouveau.

En production (Fly.io) : fly ssh console -C "python scripts/create_api_client.py --name ..."
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.crud import create_api_client  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.security import generate_api_key  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Crée un client de l'API et affiche sa clé.")
    parser.add_argument("--name", required=True, help="nom unique du client")
    parser.add_argument("--role", choices=["predict", "admin"], default="predict")
    args = parser.parse_args()

    api_key = generate_api_key()
    session = get_session_factory()()
    try:
        client = create_api_client(session, args.name, api_key, args.role)
        session.commit()
    finally:
        session.close()

    print(f"Client créé : id={client.id}, nom={client.name}, rôle={client.role}")
    print(f"Clé d'API (à conserver, elle ne sera plus affichée) :\n{api_key}")


if __name__ == "__main__":
    main()
