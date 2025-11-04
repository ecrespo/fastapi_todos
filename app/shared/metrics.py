from __future__ import annotations

from time import perf_counter
from typing import Callable, Awaitable

from prometheus_client import Counter, Histogram, Gauge

# HTTP metrics (specifically for todos endpoints, but can be used elsewhere)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path", "status"),
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

# Database metrics

db_connection_attempts_total = Counter(
    "db_connection_attempts_total",
    "Total attempts to acquire a DB session/connection",
    labelnames=("result",),  # success|failure
)

db_queries_total = Counter(
    "db_queries_total",
    "Total raw SQL queries executed",
    labelnames=("statement", "result"),  # result: success|failure
)

# Duration of queries (regardless of success)
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "SQL query duration in seconds",
    labelnames=("statement", "result"),
    buckets=(
        0.001,
        0.0025,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ),
)

# Active sessions in use (approximate; increments around usage context)
db_sessions_in_use = Gauge(
    "db_sessions_in_use",
    "Number of DB sessions currently in use (approximate)",
)


def observe_query(statement: str) -> Callable[[Callable[[], Awaitable]], Awaitable]:
    """Helper to wrap an async block that executes a query.

    Usage:
        async with query_timer("SELECT ..."):
            await session.execute(...)
    """

    async def _runner(coro_factory: Callable[[], Awaitable]):  # type: ignore[override]
        start = perf_counter()
        try:
            result = await coro_factory()
            db_queries_total.labels(statement=statement, result="success").inc()
            return result
        except Exception:
            db_queries_total.labels(statement=statement, result="failure").inc()
            raise
        finally:
            duration = perf_counter() - start
            # We don't expose raw SQL fully in production typically; here we keep a compact tag
            tag = statement.split()[0].upper() if statement else "SQL"
            db_query_duration_seconds.labels(statement=tag, result="success").observe(duration)

    return _runner
