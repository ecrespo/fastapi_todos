# FastAPI Todos

A minimal FastAPI application that exposes a simple CRUD API for todos with token-based authentication, rate limiting, logging, and a small SQLite-backed data layer. Includes pytest-based tests and Docker support with uv as the package/dependency manager.


## Overview
- REST API built with FastAPI
- Token-based auth via a bearer token stored in a local SQLite DB
- Rate limiting using slowapi
- Rich logging and latency headers via custom middlewares
- Security headers via the `secure` package
- Configurable through environment variables and optional .env files
- Packaged and run using uv; Python 3.13 is the target runtime

Key endpoints:
- GET /healthcheck (rate limited to 5/min by default)
- CRUD under /api/v1/todos
- Interactive API docs: /docs (Swagger UI) and /redoc

Authentication for /api/v1/todos requires an Authorization: Bearer <token> header. On startup, the app ensures an auth token row exists (name=auth_crud_todos). If AUTH_DEFAULT_TOKEN is not provided, one is generated and printed to the logs.


## Tech stack
- Language: Python 3.13+
- Frameworks/libraries: FastAPI, Starlette, Pydantic, slowapi, Rich, Uvicorn, SQLAlchemy (async), aiosqlite, Alembic, secure
- Package/dependency manager: uv (pyproject.toml + uv.lock)
- Testing: pytest + fastapi.testclient
- Data: SQLite
- Container: Docker (two-stage build)


## Requirements
- Python 3.13
- uv (https://github.com/astral-sh/uv)
- Optional: Docker and docker-compose

Install uv on your platform, then install project dependencies:

- uv sync --frozen


## Running locally
Default dev experience uses uv to run the app with reload.

- uv run python run.py

Environment variables honored by run.py:
- HOST: bind address (default: 0.0.0.0)
- PORT: port number (default: 8000)
- WORKERS: number of worker processes (default: 1)
- RELOAD: enable code reload (default: true). Note: when RELOAD=true, workers are forced to 1.

Alternative direct uvicorn command:
- uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

First-run auth token note:
- If you did not set AUTH_DEFAULT_TOKEN, check the app logs on startup; a token value is generated and logged (only when generated). Use it in the Authorization: Bearer <token> header for todos endpoints.

Quick smoke test (after the app is running):
- curl http://localhost:8000/healthcheck
  Expected: {"status":"ok"}


## Environment configuration
Settings are loaded via pydantic-settings. The loader resolves env files in this priority:
1) .env.<APP_ENV> where APP_ENV in {develop, staging, qa, prod}
2) .env (fallback)

Core env vars (app behavior):
- APP_ENV: environment name (develop|staging|qa|prod). Defaults to develop. Only when prod, HTTPSRedirectMiddleware is enabled.
- TODO_DB_DIR: directory for the SQLite DB file. Defaults to the settings module directory and will be created if missing.
- TODO_DB_FILENAME: DB filename; defaults to todos.db. Can be set to :memory: for an in-memory DB.
- AUTH_DEFAULT_TOKEN: when set, the app ensures an active token row with name=auth_crud_todos using this value; otherwise, a token is generated and logged at startup.
- RATE_LIMIT_EXEMPT_IPS: comma-separated IPs that bypass rate limiting (e.g., "127.0.0.1,192.168.1.10").

Runtime/process vars (used by run.py):
- HOST, PORT, WORKERS, RELOAD as described above.

Migrations (Alembic):
- DATABASE_URL: optional override for Alembic (otherwise uses alembic.ini sqlalchemy.url). See Migrations section below.

CORS is permissive by default; GZip is enabled; rate limiting is available via @limiter.limit with defaults applied to endpoints in the code.


## Using Docker
- docker-compose up --build

Notes:
- The compose file maps host 9000 to container 9000, while run.py defaults to 8000. The Dockerfile runs: `uv run --env-file .env python3 run.py`. Ensure your .env sets `PORT=9000` to match the compose mapping.
- The compose mounts ./logs and ./app into the container for live code changes and log persistence.

TODO:
- Provide a sample .env (e.g., .env.example) documenting recommended defaults, including PORT=9000 for Docker.


## Database and migrations
- The application auto-creates the schema at startup using SQLAlchemy metadata (see app/shared/db.py). This is convenient for local dev and tests.
- Alembic migrations are included under alembic/ for production-grade schema management.

Common Alembic commands:
- uv run alembic upgrade head
- uv run alembic revision -m "your message" --autogenerate

Configuration:
- By default, alembic.ini points to `sqlite+aiosqlite:///./app/shared/todos.db`.
- You can override with `DATABASE_URL` env var (e.g., `export DATABASE_URL=sqlite+aiosqlite:///./my.db`).


## Tests
Run all tests:
- uv run pytest -q

Examples:
- uv run pytest -q tests/test_todos_unit.py
- uv run pytest -q tests/test_todos_unit.py::test_create_todo

Testing notes:
- tests/conftest.py provides a TestClient fixture that creates a temporary SQLite DB, initializes schema, and seeds an active token 'test-token'. It also configures Authorization headers so you can call protected endpoints directly in tests.
- For unit-style tests without DB side-effects, monkeypatch the module-level service used by the router as shown in tests/test_todos_unit.py.


## Project structure
- app/
  - main.py: FastAPI app and middleware setup; healthcheck; router mounting; startup DB init and auth token bootstrap.
  - api/v1/todos.py: Todos API endpoints with auth and rate limiting.
  - shared/: settings (pydantic-settings), DB helpers and models (SQLAlchemy), auth, rate limiter (slowapi), and logging (Rich-based).
  - services/: TodoService implementing domain logic.
  - repositories/: persistence using SQLAlchemy AsyncSession and raw SQL text queries.
  - middlewares/: custom error handling, request logging, process time header.
  - models/: request/response models (Pydantic v2).
- alembic/: migration environment and versions.
- run.py: convenience launcher wrapping uvicorn with env-var controls.
- pyproject.toml: metadata and dependencies; requires Python >=3.13.
- Dockerfile: two-stage image using uv for dependency management.
- docker-compose.yaml: local development; exposes 9000:9000 and mounts code/log volumes.
- tests/: pytest suite using fastapi.testclient.


## Scripts and entry points
- uv-based:
  - uv sync --frozen
  - uv run python run.py
  - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  - uv run alembic upgrade head
- Docker:
  - docker-compose up --build
- App entry points:
  - run.py main() → starts Uvicorn and serves app.main:app
  - app.main:app → importable ASGI app for uvicorn/gunicorn


## License
This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See LICENSE for details.


## Additional notes and TODOs
- Security hardening, CORS restrictions, and rate limit policies for production are TBD.
- Provide API documentation snippets and examples for each todos endpoint (for now, rely on FastAPI docs at /docs once the app is running).
- Add an .env.example so new users can run docker-compose without manual edits.
- Decide on a canonical DB migration workflow for non-dev environments (auto-create vs. Alembic-only) and document it.