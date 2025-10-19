Project Development Guidelines

This document captures project-specific knowledge for developing, testing, and running the FastAPI Todos application. It assumes senior-level familiarity with Python, FastAPI, uv, pytest, and containerized workflows.

1. Build and Configuration

- Python/runtime and deps
  - Python 3.13 is the target runtime (see pyproject.toml and Dockerfile).
  - Dependency management: uv (Astral). The repo includes pyproject.toml and uv.lock.
    - Sync/install: uv sync --frozen
    - Run commands in the venv: uv run <cmd>
- Local app run
  - Direct (reload by default):
    - uv run python run.py
    - Optional env vars (see run.py): HOST, PORT, WORKERS, RELOAD. If RELOAD=true, workers are forced to 1.
  - Uvicorn alternative:
    - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
- Configuration via environment
  - Settings are defined with pydantic-settings in app/shared/config.py. The loader resolves an env file in priority:
    - .env.<APP_ENV> where APP_ENV in {develop, staging, qa, prod}, then fallback to .env if present.
  - Key settings:
    - APP_ENV: defaults to develop. Controls https redirect behavior (enabled only in prod) and env file resolution.
    - TODO_DB_DIR: directory for the SQLite DB file (default: the settings module dir). Will be created if missing.
    - TODO_DB_FILENAME: the DB filename (default: todos.db). Can be set to :memory: for an ephemeral DB (supported by sqlite).
  - Auth token bootstrap at startup (see app/main.py and app/shared/db.ensure_auth_token):
    - AUTH_DEFAULT_TOKEN: if provided, the app will ensure an active token row with name=auth_crud_todos using the given value; otherwise a token is generated and logged on startup.
- Middleware and operational implications
  - TrustedHostMiddleware allows all by default.
  - HTTPSRedirectMiddleware is added only when APP_ENV=prod.
  - CORSMiddleware is permissive by default (all origins/methods/headers; no credentials).
  - GZipMiddleware enabled.
  - Custom middlewares: LoggingMiddleware, ProcessTimeHeaderMiddleware, ErrorHandlingMiddleware (outermost).
  - Rate limiting via slowapi (see app/shared/rate_limiter.py). Endpoints can be decorated with @limiter.limit; /healthcheck is limited to 5/min.
- Docker
  - Production-minded, two-stage Dockerfile using uv.
  - Build and run with docker-compose:
    - docker-compose up --build
    - Exposes port 9000:9000. The run command in the container uses uv run --env-file .env python3 run.py. Ensure .env is present if needed.
  - Mounted volumes: ./logs and ./app for live code changes.

2. Testing

- Test stack
  - pytest is used (see [tool.pytest.ini_options] pythonpath = ["."]).
  - Tests are under tests/ and use fastapi.testclient.TestClient.
- DB and auth isolation in tests
  - tests/conftest.py provides a module-scoped client fixture that:
    - Creates a temp sqlite DB file for the module and sets app.shared.db.DB_PATH to it.
    - Calls init_db() to create schema.
    - Seeds an active auth token 'test-token' and provides a TestClient with Authorization: Bearer test-token.
  - For unit style isolation, tests can override the repository/service used by the router (see tests/test_todos_unit.py using monkeypatch and a MockRepository). That test also sets a temp DB because auth token validation reads the DB.
- Running tests
  - All tests:
    - uv run pytest -q
  - Single test file:
    - uv run pytest -q tests/test_todos_unit.py
  - Single test (node id):
    - uv run pytest -q tests/test_todos_unit.py::test_create_todo
- Adding a new test
  - Prefer using the shared client fixture when you need to exercise the full stack, including auth and middlewares:
    - from fastapi.testclient import TestClient
    - def test_something(client: TestClient):
        # DB is temp and auth token already seeded by the fixture
        resp = client.get("/api/v1/todos/")
        assert resp.status_code == 200
  - If you need to control data without DB side-effects, monkeypatch the module-level service used by the router:
    - import app.api.v1.todos as todos_module
    - monkeypatch.setattr(todos_module, "service", my_fake_service, raising=True)
    - Still use a temp DB or mock auth if your request hits auth validation.
  - For endpoints protected by auth, include the Authorization header if you create your own TestClient instance. The shared fixture already does this for you.
- Demo test flow (verified)
  - Example content that passes using the shared client fixture:
    - File (illustrative):
      from fastapi.testclient import TestClient
      from app.main import app  # ensures the app is imported and startup hooks run in TestClient
      def test_demo_create_and_get(client: TestClient):
          resp_create = client.post("/api/v1/todos/", json={"id": 42, "item": "demo-item"})
          assert resp_create.status_code == 200
          resp_get = client.get("/api/v1/todos/42")
          assert resp_get.status_code == 200
          assert resp_get.json() == {"todo": {"id": 42, "item": "demo-item"}}
    - Run:
      uv run pytest -q path/to/that_test.py
    - Notes: The example above was executed locally and passed before writing these guidelines.

3. Additional development information

- API authentication
  - Endpoints under /api/v1/todos require a valid bearer token present in the auth_tokens table (see app/shared/auth.py). Tests/fixtures insert an active token and pass it via the Authorization header.
- Database layer
  - SQLite with a minimal schema managed in app/shared/db.py. DB_PATH is derived from Settings.db_path at import time; tests override app.shared.db.DB_PATH directly before calling init_db(). If you need to re-point the DB at runtime, ensure the module-level DB_PATH is updated prior to connection creation.
- Service and repository abstraction
  - app/services/todo_service.py mediates domain logic over a repository interface implemented in app/repositories/todo_repository.py. The API router (app/api/v1/todos.py) consumes a module-level service instance; tests can monkeypatch this to replace storage with fakes.
- Rate limiting in tests
  - slowapi is initialized in app.main. For typical unit tests with TestClient, rate limits are high enough not to interfere. If you add tests that call the same limited endpoint in a loop, consider adjusting limits for that test via monkeypatching the decorator target or calling distinct endpoints.
- Logging and diagnostics
  - LoggerSingleton provides a Rich-based logger. Middlewares log request/response info and add X-Process-Time headers for latency diagnostics. Log files are written under ./logs (see docker-compose for volume mapping and examples already present in the repo).
- HTTPS redirect behavior
  - Active only in APP_ENV=prod; local/dev/tests are unaffected. Be aware if you set APP_ENV=prod in local dev, HTTP will redirect to HTTPS which can break test assumptions.
- Code style and linters
  - The repo doesn’t enforce a formatter or linter config. Follow standard modern Python idioms, type hints, and keep modules small. Tests should be explicit and isolated, in the style used by tests/test_todos_unit.py and tests/test_healthcheck.py.

Appendix: Quickstart snippets

- Install dependencies
  - uv sync --frozen
- Run app locally
  - uv run python run.py
- Run all tests
  - uv run pytest -q
- Run within Docker
  - docker-compose up --build
