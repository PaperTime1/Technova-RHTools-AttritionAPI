.PHONY: help install dev test lint format run docker-build up down logs db-create db-insert api-client

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances
	uv pip install --system .

dev: ## Installe les dépendances (dev inclus)
	uv pip install --system ".[dev]"

test: ## Lance les tests avec couverture
	pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=html

lint: ## Vérifie le code avec Ruff
	ruff check app/ tests/ scripts/
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

up: ## Déploie en local : base + initialisation + API (docker compose)
	docker compose up -d

down: ## Arrête la pile (les données restent dans le volume pgdata)
	docker compose down

logs: ## Suit les logs de l'API
	docker compose logs -f api

api-client: ## Crée un client de l'API (usage : make api-client NAME=rh ROLE=predict)
	python scripts/create_api_client.py --name $(NAME) --role $(or $(ROLE),predict)
