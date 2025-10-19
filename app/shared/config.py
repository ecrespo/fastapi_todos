from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


class Environment(str, Enum):
    develop = "develop"
    staging = "staging"
    qa = "qa"
    prod = "prod"


def _resolve_env_file(env: str | Environment | None) -> Optional[str]:
    # Priority: explicit APP_ENV/ENVIRONMENT-specific file -> generic .env
    # e.g., .env.develop, .env.staging, .env.qa, .env.prod
    env_name = str(env or "").strip().lower()
    if env_name in {e.value for e in Environment}:
        candidate = Path(".env." + env_name)
        if candidate.exists():
            return str(candidate)
    # fallback to root .env if it exists
    if Path(".env").exists():
        return ".env"
    return None


class Settings(BaseSettings):
    # Core app settings
    environment: Environment = Field(default=Environment.develop, alias="APP_ENV")
    debug: bool = False
    app_name: str = "FastAPI Todos"

    # Database selection and connection
    # Primary switch: which backend to use. Defaults to sqlite to preserve tests behavior.
    db_engine: str = Field(default="sqlite", alias="DB_ENGINE")  # one of: sqlite, mysql, postgresql
    # Optional full DATABASE_URL; if provided, it takes precedence over individual params.
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # SQLite-specific settings (kept for backward compatibility with tests)
    # Directory where DB file should be stored; default to the package directory
    todo_db_dir: Path = Field(default=Path(__file__).parent, alias="TODO_DB_DIR")
    # Database filename, e.g., todos.db or :memory:
    todo_db_filename: str = Field(default="todos.db", alias="TODO_DB_FILENAME")

    # Generic connection parts for MySQL/PostgreSQL (used if database_url not set)
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int | None = Field(default=None, alias="DB_PORT")
    db_user: str | None = Field(default=None, alias="DB_USER")
    db_password: str | None = Field(default=None, alias="DB_PASSWORD")
    db_name: str | None = Field(default=None, alias="DB_NAME")

    # Redis configuration (optional; dedicated RedisSettings is also provided)
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # Celery configuration (RabbitMQ by default; tests may set eager mode)
    celery_broker_url: str = Field(default="pyamqp://guest@localhost//", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="rpc://", alias="CELERY_RESULT_BACKEND")
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def db_path(self) -> Path:
        # If special in-memory filename, keep as-is (sqlite accepts ':memory:')
        if self.todo_db_filename == ":memory:":
            return Path(self.todo_db_filename)
        # Ensure directory exists
        try:
            self.todo_db_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Do not fail if cannot create; sqlite will error later
            pass
        return self.todo_db_dir / self.todo_db_filename


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Create a temporary settings to resolve env file, then instantiate again so env_file takes effect
    temp = Settings()
    # If an env file is available based on temp.environment, load it with python-dotenv and re-instantiate so env_file takes effect
    env_file = _resolve_env_file(temp.environment)
    if env_file:
        # Preload environment for non-pydantic consumers as well
        load_dotenv(dotenv_path=env_file, override=False, encoding="utf-8")
        return Settings(_env_file=env_file)
    # Also try loading a generic .env if present (no override so OS env wins)
    if Path(".env").exists():
        load_dotenv(dotenv_path=".env", override=False, encoding="utf-8")
    return temp
