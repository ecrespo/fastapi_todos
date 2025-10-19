ARG PYTHON_VERSION=3.13.9
ARG UV_VERSION=latest

# Build stage: Install dependencies
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Runtime stage: Minimal production image
FROM python:${PYTHON_VERSION}-slim-trixie

LABEL authors="Ernesto Crespo <ernesto@asistensi.com>"
LABEL description="FastAPI ToDO Application"

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy uv for runtime
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /bin/

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser .env .

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["uv", "run", "--env-file", ".env", "python3", "run.py"]