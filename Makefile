.PHONY: help install-backend install-frontend dev-backend dev-frontend test-backend test-frontend build-frontend lint format migrate create-admin mock-devices seed-demo clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Installation ─────────────────────────────────────────────────────────────

install-backend: ## Install backend dependencies
	cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

# ── Development ──────────────────────────────────────────────────────────────

dev-backend: ## Run backend dev server
	cd backend && .venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend dev server
	cd frontend && npm run dev

# ── Testing ──────────────────────────────────────────────────────────────────

test-backend: ## Run backend tests
	cd backend && .venv\Scripts\python -m pytest tests/ -v --tb=short

test-frontend: ## Run frontend tests
	cd frontend && npm run test

test: test-backend test-frontend ## Run all tests

# ── Build ────────────────────────────────────────────────────────────────────

build-frontend: ## Build frontend for production
	cd frontend && npm run build

# ── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Run linters
	cd backend && .venv\Scripts\python -m ruff check app/ tests/
	cd frontend && npm run lint

format: ## Format code
	cd backend && .venv\Scripts\python -m ruff format app/ tests/

typecheck: ## Run type checking
	cd backend && .venv\Scripts\python -m mypy app/

# ── Database ─────────────────────────────────────────────────────────────────

migrate: ## Run database migrations
	cd backend && .venv\Scripts\python -m alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	cd backend && .venv\Scripts\python -m alembic revision --autogenerate -m "$(MSG)"

# ── Utilities ────────────────────────────────────────────────────────────────

create-admin: ## Create admin user
	cd backend && .venv\Scripts\python -m scripts.create_admin

mock-devices: ## Run mock device simulator
	cd backend && .venv\Scripts\python -m scripts.mock_device

seed-demo: ## Seed demo data
	cd backend && .venv\Scripts\python -m scripts.seed_demo_data

api-schema: ## Generate OpenAPI schema
	cd backend && .venv\Scripts\python -m scripts.generate_api_schema

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Clean build artifacts
	rm -rf frontend/dist frontend/node_modules/.vite
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
