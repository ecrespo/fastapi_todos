from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Database settings (sqlite for this project tests)
    # Directory where DB file should be stored; default to the package directory
    todo_db_dir: Path = Field(default=Path(__file__).parent, alias="TODO_DB_DIR")
    # Database filename, e.g., todos.db or :memory:
    todo_db_filename: str = Field(default="todos.db", alias="TODO_DB_FILENAME")

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
    # If an env file is available based on temp.environment, re-instantiate so it is applied
    env_file = _resolve_env_file(temp.environment)
    if env_file:
        return Settings(_env_file=env_file)
    return temp
