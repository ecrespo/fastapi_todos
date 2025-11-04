from __future__ import annotations

import json
import os
from typing import Any

from redis import asyncio as aioredis

# Default TTL for cached todos in seconds (can be configured via env)
CACHE_TTL: int = int(os.getenv("REDIS_TODOS_TTL", "60"))


def _todo_key(todo_id: int) -> str:
    """Build the Redis cache key for a single todo id."""
    return f"todos:{todo_id}"


async def _cache_get_json(redis_client: aioredis.Redis, key: str) -> Any | None:
    """Safely get and decode a JSON payload from Redis. Returns None on any error."""
    try:
        value = await redis_client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        return None


async def _cache_set_json(
    redis_client: aioredis.Redis,
    key: str,
    value: Any,
    ex: int = CACHE_TTL,
) -> None:
    """Safely encode and set a JSON payload in Redis with optional TTL."""
    try:
        await redis_client.set(key, json.dumps(value), ex=ex)
    except Exception:
        # Silently ignore cache set errors
        pass


async def _cache_delete(redis_client: aioredis.Redis, *keys: str) -> None:
    """Safely delete one or more keys from Redis. No-op on errors."""
    try:
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        # Silently ignore cache delete errors
        pass
