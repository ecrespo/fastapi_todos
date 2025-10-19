# FastAPI Todos

A minimal FastAPI application that exposes a simple CRUD API for todos with token-based authentication, rate limiting, logging, and a small SQLite-backed data layer. Includes pytest-based tests and Docker support with uv as the package/dependency manager.

## Documentation
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
- Project Development Guidelines: [.junie/guidelines.md](./.junie/guidelines.md)

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
- GET /redis-check
- CRUD under /api/v1/todos
- Interactive API docs: /docs (Swagger UI) and /redoc

Authentication for /api/v1/todos requires an Authorization: Bearer <token> header. On startup, the app ensures an auth token row exists (name=auth_crud_todos). If AUTH_DEFAULT_TOKEN is not provided, one is generated and printed to the logs.


## Tech stack
- Language: Python 3.13+
- Frameworks/libraries: FastAPI, Starlette, Pydantic, slowapi, Rich, Uvicorn, SQLAlchemy (async), aiosqlite, Alembic, secure, Redis (redis-py), Celery
- Package/dependency manager: uv (pyproject.toml + uv.lock)
- Testing: pytest + fastapi.testclient
- Data: SQLite, PostgreSQL, MySQL
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
- TODO: Document any rate limiting exemption configuration if/when implemented.

Database configuration (runtime):
- DB_ENGINE: database backend (sqlite|mysql|postgresql). Defaults to sqlite for local dev/tests.
- DATABASE_URL: optional full DSN that takes precedence over granular settings.
  Examples:
  - SQLite memory: sqlite+aiosqlite://
  - SQLite file:   sqlite+aiosqlite:///./app/shared/todos.db
  - MySQL:         mysql+aiomysql://user:password@localhost:3306/todos
  - PostgreSQL:    postgresql+asyncpg://user:password@localhost:5432/todos
- DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME: used when DATABASE_URL is not set. Note: default DB_PORT varies by engine (3306 for MySQL, 5432 for PostgreSQL).

Redis (optional; used by /redis-check):
- REDIS_HOST (default localhost), REDIS_PORT (default 6379), REDIS_DB (default 0). See app/shared/redis_settings.py.

Celery (optional; background task processing):
- CELERY_BROKER_URL (default in config points to local RabbitMQ; see app/shared/config.py and docker-compose.yaml)
- CELERY_RESULT_BACKEND (default: rpc://)
- CELERY_TASK_ALWAYS_EAGER (set true in tests or dev to execute tasks inline without a broker)

Runtime/process vars (used by run.py):
- HOST, PORT, WORKERS, RELOAD as described above.

Migrations (Alembic):
- DATABASE_URL: optional override for Alembic (otherwise uses alembic.ini sqlalchemy.url). See Migrations section below.

CORS is permissive by default; GZip is enabled; rate limiting is available via @limiter.limit with defaults applied to endpoints in the code.


## Using Docker
- docker-compose up --build

Notes:
- docker-compose maps host 8000 to container 8000. The image runs `uv run --env-file .env python3 run.py` and run.py defaults to PORT=8000, so no extra PORT override is required. If you change PORT in .env, update the compose ports accordingly.
- Volumes: ./logs and ./app are mounted for live code changes and log persistence. The .env file is mounted read-only.
- Services: docker-compose provisions Redis, RabbitMQ, a Celery worker, and PostgreSQL for local development. PostgreSQL is exposed on the host via POSTGRES_HOST_PORT (defaults to 55432 if not set). See docker-compose.yaml for details.
- Timezone: Set TZ=America/Caracas in your .env file. All services in docker-compose load .env via env_file, so they share the same timezone.

TODO:
- Provide a sample .env (e.g., .env.example) documenting recommended defaults (APP_ENV, DB_ENGINE/DATABASE_URL, AUTH_DEFAULT_TOKEN, Redis/Postgres settings, TZ, etc.).


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
  - tasks/: Celery tasks for background processing.
- alembic/: migration environment and versions.
- run.py: convenience launcher wrapping uvicorn with env-var controls.
- pyproject.toml: metadata and dependencies; requires Python >=3.13.
- Dockerfile: two-stage image using uv for dependency management.
- docker-compose.yaml: local development; exposes 8000:8000 and mounts code/log volumes.
- tests/: pytest suite using fastapi.testclient.


## Scripts and entry points
- uv-based:
  - uv sync --frozen
  - uv run python run.py
  - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  - uv run alembic upgrade head
  - uv run pytest -q
  - uv run celery -A app.shared.celery_app:celery_app worker --loglevel=INFO -Q celery
- Docker:
  - docker-compose up --build
- App entry points:
  - run.py main() → starts Uvicorn and serves app.main:app
  - app.main:app → importable ASGI app for uvicorn/gunicorn


## Makefile
The repository includes a Makefile to streamline common developer tasks. Run `make help` to list available targets.

Key targets:
- help: Show available targets and descriptions
- install: Install project dependencies using uv (frozen from uv.lock)
- run: Run the FastAPI app locally via run.py (uv run python run.py)
- up: Start services with docker compose (foreground, rebuild)
- up-d: Start services with docker compose (detached, rebuild)
- down: Stop services and remove containers
- logs: Follow docker compose logs
- restart: Restart services (down + up -d)
- test: Run all tests (pytest -q)
- test-file: Run tests for a specific file; usage: make test-file FILE=tests/test_todos_unit.py
- test-node: Run a single test node; usage: make test-node NODE=tests/test_todos_unit.py::test_create_todo
- lint: Run ruff static analysis over app, tests, run.py
- imports: Validate import order only (ruff isort rules)
- naming: Validate naming conventions only (pep8-naming)
- format: Format code with ruff and fix import order
- types: Run static type checks with mypy
- security: Audit installed dependencies with pip-audit
- check: Run lint, types, tests, and security in sequence

Examples:
- make help
- make install
- make run
- make test
- make test-file FILE=tests/test_todos_unit.py
- make test-node NODE=tests/test_todos_unit.py::test_create_todo
- make lint
- make format
- make types
- make check

## License
This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See LICENSE for details.


## Additional notes and TODOs
- Security hardening, CORS restrictions, and rate limit policies for production are TBD.
- Provide API documentation snippets and examples for each todos endpoint (for now, rely on FastAPI docs at /docs once the app is running).
- Add an .env.example so new users can run docker-compose without manual edits.
- Decide on a canonical DB migration workflow for non-dev environments (auto-create vs. Alembic-only) and document it.

## Project Development Guidelines (FastAPI Todos)

Audience: Senior Python/FastAPI engineers. This document captures project-specific, verified workflows and caveats to accelerate development and debugging.

1) Build and Configuration

- Runtime and package management
  - Target Python: 3.13 (see pyproject.toml and Dockerfile).
  - Dependency manager: uv (Astral). Locked via uv.lock.
  - Install deps (frozen):
    - uv sync --frozen
  - Run commands in the venv:
    - uv run <command>

- Running the application locally
  - Default dev run (auto-reload):
    - uv run python run.py
  - Uvicorn alternative:
    - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  - Config via env (pydantic-settings; see app/shared/config.py). The loader resolves env files in this order:
    - .env.<APP_ENV> where APP_ENV in {develop, staging, qa, prod}
    - .env (fallback)
  - Key envs:
    - APP_ENV: defaults to develop. HTTPS redirect middleware only turns on when APP_ENV=prod.
    - TODO_DB_DIR: directory for the SQLite DB (defaults to settings module dir); created if missing.
    - TODO_DB_FILENAME: DB filename (default: todos.db). Set to :memory: for an in-memory SQLite database.

- Auth token bootstrap at startup
  - On startup, app/shared/db.ensure_auth_token_async ensures an active token row with name=auth_crud_todos.
  - Provide AUTH_DEFAULT_TOKEN to fix the token value; otherwise a token is generated and logged at startup. Tests seed their own token; see below.

- Middleware (operational implications)
  - TrustedHostMiddleware: allows all by default.
  - HTTPSRedirectMiddleware: only when APP_ENV=prod (beware if you export APP_ENV=prod locally; HTTP will redirect to HTTPS and can break assumptions/tests).
  - CORSMiddleware: permissive (all origins/methods/headers; credentials disabled).
  - GZipMiddleware: enabled.
  - Custom middlewares (outermost first): ErrorHandlingMiddleware, then LoggingMiddleware, ProcessTimeHeaderMiddleware.
  - Rate limiting via slowapi (see app/shared/rate_limiter.py). Use @limiter.limit on endpoints; /healthcheck limited to 5/min by default.

- Docker
  - Two-stage Dockerfile using uv.
  - docker-compose up --build exposes 8000:8000.
  - Entrypoint runs: uv run --env-file .env python3 run.py (ensure .env exists if you rely on it).
  - Volumes: ./logs and ./app mounted for live code changes.

2) Testing

- Stack
  - pytest with pythonpath = ["."] configured in pyproject.toml.
  - Tests under tests/ use fastapi.testclient.TestClient.

- DB and auth isolation (critical for correctness)
  - tests/conftest.py provides a module-scoped client fixture that:
    - Creates a temporary sqlite DB path per test module and points app.shared.db.DB_PATH to it.
    - Calls init_db() to create schema.
    - Inserts an active token 'test-token' into auth_tokens and constructs TestClient with Authorization: Bearer test-token.
  - If you create your own TestClient outside the shared fixture, include the Authorization header; otherwise the todos endpoints will 401.

- Running tests
  - All tests: uv run pytest -q
  - Single file: uv run pytest -q tests/test_todos_unit.py
  - Single test (node id): uv run pytest -q tests/test_todos_unit.py::test_create_todo

- Adding a new test (full-stack path, recommended)
  - Prefer the shared client fixture when you want to exercise middlewares, auth, rate limiting, and DB:
    from fastapi.testclient import TestClient

    def test_demo_create_and_get(client: TestClient):
        resp_create = client.post("/api/v1/todos/", json={"id": 42, "item": "demo-item"})
        assert resp_create.status_code == 200
        # Message content varies; accept the canonical messages used by the app
        assert resp_create.json()["message"].lower() in {
            "created",
            "todo created",
            "created successfully",
            "todo has been created successfully!",
        }

        resp_get = client.get("/api/v1/todos/42")
        assert resp_get.status_code == 200
        data = resp_get.json()
        assert "todo" in data
        assert data["todo"]["id"] == 42
        assert data["todo"]["item"] == "demo-item"
        assert "status" in data["todo"]
        assert "created_at" in data["todo"]

- Adding a unit-style test without DB side-effects
  - Monkeypatch the module-level service used by the router to a fake service. See tests/test_todos_unit.py for the pattern:
    import app.api.v1.todos as todos_module
    monkeypatch.setattr(todos_module, "service", my_fake_service, raising=True)
  - Note: Even unit tests may indirectly touch auth validation; if so, still leverage the temp DB from the shared fixture or mock auth.

- Rate limiting in tests
  - slowapi is initialized in app.main. Current limits are high enough to not interfere with typical TestClient flows.
  - If you loop heavily over the same limited endpoint, either increase limits for that test via monkeypatch or distribute calls across endpoints.

- Verified flows (executed locally before writing this document)
  - On 2025-10-19 12:33 local time:
    - Baseline run: uv run pytest -q -> 9 passed.
    - Demo test (temporary file tests/test_demo_guidelines.py):
      - uv run pytest -q tests/test_demo_guidelines.py -> 1 passed.
      - The temporary test file was removed afterward to keep the repo clean.

3) Additional Development Information

- API authentication
  - All /api/v1/todos endpoints require a Bearer token that exists and is active in auth_tokens (see app/shared/auth.py). The shared test fixture inserts 'test-token' and preconfigures Authorization headers on the TestClient.

- Database layer
  - SQLite with SQLAlchemy Async engine and declarative models defined in app/shared/db.py. Schema is created via Base.metadata.create_all at startup (init_db_async in app.main lifespan) and in tests via init_db().
  - DB connection URL is derived from Settings + DB_ENGINE/DATABASE_URL at import/runtime; tests override app.shared.db.DB_PATH prior to connection creation. init_db() resets the async engine so re-pointing DB_PATH takes effect.
  - If you need to re-point the DB at runtime, update the module-level DB_PATH before obtaining new connections.
  - Todo model fields include: id, item, created_at (server default CURRENT_TIMESTAMP), and status (Enum: start, in_process, pending, done, cancel; default pending).
  - ensure_auth_token/ensure_auth_token_async use sqlite3/async engine to ensure compatibility with test setup.
  - For PostgreSQL bootstrap in containers, see sql/init_postgres.sql (idempotent type/table creation for enums and tables).

- Service and repository abstraction
  - app/services/todo_service.py encapsulates domain logic.
  - app/repositories/todo_repository.py implements persistence against SQLite.
  - app/api/v1/todos.py consumes a module-level TodoService instance (service). Tests can monkeypatch this symbol for isolation.

- Logging and diagnostics
  - LoggerSingleton provides a Rich-based logger. Request/response logging and X-Process-Time headers are added by middlewares. Logs are written to ./logs; docker-compose mounts this directory for convenience.

- HTTPS redirect behavior
  - Only active when APP_ENV=prod. If you enable it during local dev, HTTP traffic to the app will redirect to HTTPS, which can break your tests or curl scripts.

- Code style and conventions
  - No enforced linter/formatter in-repo; follow modern Python idioms and type hints. Keep modules cohesive and small. Tests should be explicit and isolated, similar to tests/test_todos_unit.py and tests/test_healthcheck.py.

- Practical debugging tips specific to this codebase
  - If authorization unexpectedly fails in tests, verify the client fixture is used and that the Authorization header is present.
  - If DB writes appear to be missing, confirm the test is using the temp DB path and that init_db() has been called before the request.
  - Rate-limited endpoints return 429s; in tests, look for repeated calls to the same limited route within one minute.
  - To observe startup token generation in dev, run the app and check the console logs for the generated token when AUTH_DEFAULT_TOKEN is not provided.

Appendix: Quickstart
- Install deps: uv sync --frozen
- Run app: uv run python run.py
- Run all tests: uv run pytest -q
- Run within Docker: docker-compose up --build



### Database backend selection (sqlite, mysql, postgresql)

This project now supports selecting the database backend via environment variables using Factory and Strategy patterns under app/shared/db.py.

- Default backend is SQLite (aiosqlite) and is used by tests.
- To select another backend, set the following env vars (examples):

1) SQLite (default)
- DB_ENGINE=sqlite
- TODO_DB_DIR=./app/shared
- TODO_DB_FILENAME=todos.db

2) MySQL (requires aiomysql)
- DB_ENGINE=mysql
- DB_HOST=localhost
- DB_PORT=3306
- DB_USER=root
- DB_PASSWORD=secret
- DB_NAME=todos
# Or provide a full URL
# DATABASE_URL=mysql+aiomysql://root:secret@localhost:3306/todos

3) PostgreSQL (requires asyncpg)
- DB_ENGINE=postgresql
- DB_HOST=localhost
- DB_PORT=5432
- DB_USER=postgres
- DB_PASSWORD=secret
- DB_NAME=todos
# Or provide a full URL
# DATABASE_URL=postgresql+asyncpg://postgres:secret@localhost:5432/todos

Notes:
- If you choose MySQL or PostgreSQL, ensure the appropriate async driver is installed: aiomysql or asyncpg.
- On startup, the application creates tables via SQLAlchemy Base.metadata.create_all for the selected backend.
- The auth token bootstrap now uses an async path that works across backends.
