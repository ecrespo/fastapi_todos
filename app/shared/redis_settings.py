from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import asyncio as aioredis


class RedisSettings(BaseSettings):
    """
    Simple Redis settings backed by environment variables.

    Variables:
    - REDIS_HOST: hostname or service name (default: localhost)
    - REDIS_PORT: TCP port (default: 6379)
    - REDIS_DB: database index (default: 0)
    """

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    def get_redis_url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


@lru_cache(maxsize=1)
def get_redis_settings() -> RedisSettings:
    return RedisSettings()


# A lightweight, lazily-initialized singleton Redis client for DI
_cached_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """
    FastAPI dependency provider that returns a shared asyncio Redis client.

    The client is created on first use using settings from environment variables.
    Connections are managed by redis-py; callers should not close the client.
    """
    global _cached_client
    if _cached_client is None:
        settings = get_redis_settings()
        _cached_client = aioredis.from_url(
            settings.get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _cached_client
