# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# uv épinglé (reproductibilité du build)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# 1. Dépendances d'abord : cette couche reste en cache tant que pyproject.toml ne change pas
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

# 2. Code, artefacts du modèle, scripts d'initialisation de la base et dataset
COPY app/ app/
COPY artifacts/ artifacts/
COPY scripts/ scripts/
COPY data/ data/

# 3. Exécution sans privilèges root
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
