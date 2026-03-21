.PHONY: help install dev test lint run docker-build docker-run db-create db-insert deploy

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances
	uv pip install --system .

dev: ## Installe les dépendances (dev inclus)
	uv pip install --system ".[dev]"

test: ## Lance les tests avec couverture
	pytest --cov=app --cov-report=term-missing --cov-report=html

lint: ## Vérifie le code avec Ruff
	ruff check app/ tests/
	ruff format --check app/ tests/

format: ## Formate le code
	ruff format app/ tests/

run: ## Lance l'API en local
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

db-create: ## Crée la base de données et les tables
	python scripts/create_db.py

db-insert: ## Insère le dataset dans la base
	python scripts/insert_dataset.py

docker-build: ## Build l'image Docker
	docker build -t technova-attrition-api .

docker-run: ## Lance le container Docker
	docker run -p 8000:8000 --env-file .env technova-attrition-api

deploy: ## Déploie sur Fly.io
	flyctl deploy --remote-only
