Project Development Guidelines (FastAPI Todos)

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
  - On startup, app/shared/db.ensure_auth_token ensures an active token row with name=auth_crud_todos.
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
  - docker-compose up --build exposes 9000:9000.
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
        assert resp_get.json() == {"todo": {"id": 42, "item": "demo-item"}}

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
  - SQLite with minimal schema managed in app/shared/db.py. DB_PATH is derived from Settings.db_path at import time; tests override app.shared.db.DB_PATH prior to connection creation and then call init_db().
  - If you need to re-point the DB at runtime, update the module-level DB_PATH before obtaining new connections.

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
