FROM python:3.11-slim

WORKDIR /app

# Installer uv pour la gestion des dépendances
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copier les fichiers de dépendances
COPY pyproject.toml .

# Installer les dépendances (sans dev)
RUN uv pip install --system --no-cache -r pyproject.toml

# Copier le code source et les artefacts
COPY app/ app/
COPY artifacts/ artifacts/

# Port exposé
EXPOSE 8000

# Lancement
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
