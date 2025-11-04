Project Development Guidelines (FastAPI Todos)

Audience: Senior Python/FastAPI engineers. This document captures project‑specific, verified workflows and caveats to accelerate development and debugging. Updated to reflect the current repository state as of 2025-11-04 18:41 local time.

1) Build and Configuration

- Runtime and package management
  - Target Python: 3.13 (see pyproject.toml and Dockerfile).
  - Dependency manager: uv (Astral). Locked via uv.lock.
  - Install deps (frozen):
    - uv sync --frozen
  - Run commands in the venv:
    - uv run <command>

- Running the application locally
  - Default dev run (auto-reload via run.py env var):
    - uv run python run.py
  - Uvicorn alternative:
    - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  - Config via env (pydantic-settings; see app/shared/config.py). The loader resolves env files in this order:
    - .env.<APP_ENV> where APP_ENV in {develop, staging, qa, prod}
    - .env (fallback)
  - Key envs (core app behavior):
    - APP_ENV: defaults to develop. HTTPS redirect middleware only turns on when APP_ENV=prod.
    - TODO_DB_DIR: directory for the SQLite DB (defaults to settings module dir); created if missing.
    - TODO_DB_FILENAME: DB filename (default: todos.db). Set to :memory: for an in-memory SQLite database.
    - AUTH_DEFAULT_TOKEN: set to fix the default token value created/ensured at startup; otherwise a token is generated and logged once.
  - Rate limiting (SlowAPI):
    - RATE_LIMIT_DEFAULTS: default limits applied globally (e.g., "100/minute").
    - RATE_LIMIT_EXEMPT_IPS: comma-separated list of IPs exempt from rate limiting (e.g., 127.0.0.1,::1).
    - RATE_LIMIT_EXEMPT_PATHS: exact paths exempt from rate limiting (e.g., /docs,/redoc,/openapi.json,/metrics).
  - Database backend selection (see app/shared/db.py & README):
    - DB_ENGINE: sqlite (default), mysql, or postgresql. Primarily for local/dev defaults.
    - DATABASE_URL: full async DSN; if provided, it overrides granular parts.
      Examples:
      - sqlite+aiosqlite:// (memory)
      - sqlite+aiosqlite:///./app/shared/todos.db (file)
      - mysql+aiomysql://user:pass@localhost:3306/todos
      - postgresql+asyncpg://user:pass@localhost:5432/todos
    - If DATABASE_URL is not set, the following are used when DB_ENGINE is mysql/postgresql:
      - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
  - Redis (optional; used by /redis-check):
    - REDIS_HOST (default localhost), REDIS_PORT (6379), REDIS_DB (0). See app/shared/redis_settings.py.
  - Celery (optional; used by background tasks):
    - CELERY_BROKER_URL (default in config points to local RabbitMQ)
    - CELERY_RESULT_BACKEND (default rpc://)
    - CELERY_TASK_ALWAYS_EAGER (set true in tests to run tasks inline if needed)

- Auth token bootstrap at startup
  - On startup, app/shared/db.ensure_auth_token_async ensures an active token row with name=auth_crud_todos.
  - Provide AUTH_DEFAULT_TOKEN to fix the token value; otherwise a token is generated and logged at startup (only when generated).

- Middleware (operational implications)
  - TrustedHostMiddleware: allows all by default.
  - HTTPSRedirectMiddleware: only when APP_ENV=prod (beware if you export APP_ENV=prod locally; HTTP will redirect to HTTPS and can break assumptions/tests).
  - CORSMiddleware: permissive (all origins/methods/headers; credentials disabled).
  - GZipMiddleware: enabled.
  - Secure headers: applied via the 'secure' library in a custom HTTP middleware; Content-Security-Policy is relaxed to allow FastAPI docs assets (Swagger UI/ReDoc) from jsdelivr/redoc.ly.
  - Custom middlewares (outermost first): ErrorHandlingMiddleware, then LoggingMiddleware, ProcessTimeHeaderMiddleware.
  - Rate limiting via slowapi (see app/shared/rate_limiter.py). Use @limiter.limit on endpoints; /healthcheck limited to 5/min by default.

- Docker
  - Two-stage Dockerfile using uv.
  - docker-compose up --build exposes 8000:8000 (host:container) for the API service.
  - Entrypoint runs: uv run --env-file .env python3 run.py (ensure .env exists if you rely on it).
  - Volumes: ./logs and ./app mounted for live code changes; .env is mounted read-only into the container.
  - Port caveat: The app defaults to port 8000 (see run.py). If you change PORT in your .env, update the compose ports accordingly.
  - Timezone: Centralized via .env. Set TZ=America/Caracas in your .env. All services load .env via env_file and pass TZ=${TZ} so they share the same timezone.
  - Services: docker-compose provisions Redis, RabbitMQ, Celery worker, PostgreSQL, Prometheus, Grafana, and Traefik for local development. PostgreSQL is exposed on the host via POSTGRES_HOST_PORT (defaults to 55432 if not set). See docker-compose.yaml for details.
  - Reverse proxy (Traefik):
    - API via http://localhost (Traefik routes PathPrefix(`/`) to the api service on port 8000).
    - Dashboard: http://localhost:${TRAEFIK_DASHBOARD_PORT:-8099}. If the port is in use, set TRAEFIK_DASHBOARD_PORT in .env.
  - Observability:
    - Metrics endpoint: http://localhost:8000/metrics (exempt from rate limiting by default).
    - Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}
    - Grafana: http://localhost:${GRAFANA_PORT:-3000} (default admin/admin; change in .env)

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
        # Additional fields are present in current model
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

- Verified flows (executed locally)
  - On 2025-10-21 19:13 local time:
    - Baseline run: uv run pytest -q -> 22 passed.
    - New tests added covering auth and RBAC flows:
      - tests/test_auth_login.py
      - tests/test_first_user_admin.py
      - tests/test_rbac_todos.py

3) Additional Development Information

- API authentication and RBAC
  - All /api/v1/todos endpoints and admin user-management endpoints require a Bearer token that exists and is active in auth_tokens (see app/shared/auth.py). The shared test fixture inserts 'test-token' and preconfigures Authorization headers on the TestClient.
  - User and token model:
    - Users live in the users table with fields: id, username (unique), password_hash, role (Enum: viewer, editor, admin), active, created_at.
    - Tokens live in auth_tokens and may be linked to users via auth_tokens.user_id (nullable for legacy tokens).
    - Backward compatibility: legacy tokens without a user_id are treated as admin-equivalent in RBAC checks to avoid breaking existing flows/tests.
  - Auth endpoints (app/api/v1/auth.py):
    - POST /api/v1/auth/register: create a user. First registered user becomes admin; subsequent users default to viewer. Accepts username/user, password, confirm_password.
    - POST /api/v1/auth/login: issues an access_token (bearer) and persists it linked to the user_id.
    - GET /api/v1/auth/users: list active users. Admin only.
    - GET /api/v1/auth/users/{user_id}: get a single user. Admin only.
    - PATCH /api/v1/auth/users/{user_id}/role: update a user's role. Admin only.
    - PATCH /api/v1/auth/users/{user_id}/password: change password; allowed for admin or the same user.
  - Todos RBAC rules (app/api/v1/todos.py):
    - GET /api/v1/todos: allowed to all authenticated tokens; admins (or legacy tokens) see all todos; non-admin users see only their own (todos.user_id) and pagination/cache is scoped accordingly.
    - GET /api/v1/todos/{id}: allowed to all authenticated tokens.
    - POST /api/v1/todos/: requires editor or admin (legacy tokens allowed). Created todos are associated to the caller via todos.user_id when available.
    - PUT /api/v1/todos/{id}: requires editor or admin.
    - DELETE /api/v1/todos/{id}: requires admin.

- Database layer
  - SQLite with SQLAlchemy Async engine and declarative models defined in app/shared/db.py. Schema is created via Base.metadata.create_all at startup (init_db_async in app.main lifespan) and in tests via init_db().
  - DB connection URL is derived from Settings + DB_ENGINE/DATABASE_URL at import/runtime; tests override app.shared.db.DB_PATH prior to connection creation. init_db() resets the async engine so re-pointing DB_PATH takes effect.
  - If you need to re-point the DB at runtime, update the module-level DB_PATH before obtaining new connections.
  - Todo model fields include: id, item, created_at (server default CURRENT_TIMESTAMP), status (Enum: start, in_process, pending, done, cancel; default pending), and user_id (nullable owner link).
  - auth_tokens now include user_id (nullable) to link issued tokens to users; legacy rows without user_id remain valid.
  - Users table fields: id, username (unique), password_hash, role (Enum: viewer, editor, admin), active, created_at.
  - ensure_auth_token/ensure_auth_token_async use sqlite3/async engine to ensure compatibility with test setup.
  - For PostgreSQL bootstrap in containers, see sql/init_postgres.sql (idempotent type/table creation for enums and tables).

- Migrations (Alembic)
  - Alembic is configured (alembic.ini, alembic/env.py). The app does not run Alembic on startup; it uses SQLAlchemy create_all for schema by default.
  - Upgrade to the latest migration:
    - uv run alembic upgrade head
  - Create a new migration with autogenerate (ensure models are up-to-date and set DATABASE_URL or rely on alembic.ini):
    - uv run alembic revision --autogenerate -m "your message"
  - Recent migrations present (2025-10-21):
    - 20251019_000001_init.py
    - 20251019_000002_add_todo_created_at_status.py
    - 20251021_000003_add_user_id_to_auth_tokens.py
    - 20251021_000004_create_users_table.py
    - 20251021_000005_add_user_id_to_todos.py

- Service and repository abstraction
  - app/services/todo_service.py encapsulates domain logic.
  - app/repositories/todo_repository.py implements persistence against the configured DB (SQLite by default).
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
