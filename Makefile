# FastAPI Todos - Makefile
# Targets to run the app, docker compose flows, tests, linting, type checks, and dependency security audits.

SHELL := /bin/bash

# Tools
UV := uv
PY := $(UV) run python
PYTEST := $(UV) run pytest -q
LINT_PATHS := app tests run.py

.DEFAULT_GOAL := help

.PHONY: help install run up up-d down logs restart test test-file test-node test-cov lint imports naming format types security check

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nAvailable targets:\n\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 } /^## / { printf "\n%s\n", substr($$0,4) }' $(MAKEFILE_LIST)

install: ## Install project dependencies using uv (frozen from uv.lock)
	$(UV) sync --frozen

run: ## Run the FastAPI app locally (uses run.py defaults)
	$(PY) run.py

# Docker Compose
up: ## Start services with docker compose (foreground, rebuild)
	docker compose up --build

up-d: ## Start services with docker compose (detached, rebuild)
	docker compose up -d --build

down: ## Stop services and remove containers
	docker compose down

logs: ## Follow docker compose logs
	docker compose logs -f

restart: ## Restart services (down + up -d)
	docker compose down && docker compose up -d --build

# Testing
test: ## Run all tests (pytest -q)
	$(PYTEST)

test-file: ## Run tests for a specific file: make test-file FILE=tests/test_todos_unit.py
	@test -n "$(FILE)" || (echo "Usage: make test-file FILE=path/to/test_file.py" && exit 2)
	$(PYTEST) $(FILE)

test-node: ## Run a single test node: make test-node NODE=tests/test_file.py::test_name
	@test -n "$(NODE)" || (echo "Usage: make test-node NODE=tests/test_file.py::test_name" && exit 2)
	$(PYTEST) $(NODE)

# Coverage
# Note: coverage options are configured in pyproject.toml addopts
# Override minimum threshold with: make test-cov MIN=85
MIN ?= 0
test-cov: ## Run all tests with coverage reports (term, XML, HTML)
	$(UV) run pytest -q --cov=app --cov-report=term-missing:skip-covered --cov-report=xml --cov-report=html --cov-fail-under=$(MIN)

# Linting and formatting
lint: ## Run ruff static analysis (PEP8 errors, pyflakes, import order, upgrades, naming, etc.)
	uvx ruff check $(LINT_PATHS)

imports: ## Validate import order only (ruff isort rules)
	uvx ruff check --select I $(LINT_PATHS)

naming: ## Validate variable/function/class naming conventions only (pep8-naming)
	uvx ruff check --select N $(LINT_PATHS)

format: ## Format code with ruff and fix import order
	uvx ruff format
	uvx ruff check --select I --fix $(LINT_PATHS)

# Type checking
types: ## Run static type checks with mypy
	uvx mypy $(LINT_PATHS)

# Dependency security audit
security: install ## Audit installed dependencies for known vulnerabilities (uses pip-audit)
	uvx pip-audit -r <($(UV) run python -m pip freeze)

# Aggregate checks
check: ## Run lint, types, tests, and dependency security audit
	$(MAKE) lint && \
	$(MAKE) types && \
	$(MAKE) test && \
	$(MAKE) security
