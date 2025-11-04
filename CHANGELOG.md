# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.1.0/), and this project adheres to Semantic Versioning (https://semver.org/).

## [0.4.1] - 2025-11-04
Inferred bump: patch (infrastructure/docs updates; no breaking changes)

### Added
- Integrate Traefik as reverse proxy and update docker-compose services for local development. [bda5353](https://github.com/ecrespo/fastapi_todos/commit/bda5353)

### Changed
- Strengthened RBAC enforcement and refreshed tests/coverage. [7ca23c9](https://github.com/ecrespo/fastapi_todos/commit/7ca23c9)

### Fixed
- No user-facing fixes in this release.

### Deprecated
- None.

### Removed
- None.

### Security
- No security-related changes in this release.


## [0.4.0] - 2025-10-21
Inferred bump: minor (new features; no breaking changes detected)

### Added
- User management endpoints and role-based access control (RBAC). [cfe6742](https://github.com/ecrespo/fastapi_todos/commit/cfe6742)
- First-user admin bootstrap and enhanced user-role management. [570a565](https://github.com/ecrespo/fastapi_todos/commit/570a565)
- User-specific scoping for todos (non-admins see only their own) and coverage support. [8581a0d](https://github.com/ecrespo/fastapi_todos/commit/8581a0d)

### Changed
- Adopted Keep a Changelog format and updated project documentation. [ca2e33c](https://github.com/ecrespo/fastapi_todos/commit/ca2e33c)

### Fixed
- No user-facing fixes in this release.

### Deprecated
- None.

### Removed
- None.

### Security
- Strengthened access controls via RBAC and admin-only operations.


## [0.3.0] - 2025-10-19
Inferred bump: minor (new features added; no breaking changes detected)

### Added
- Pagination support for Todos APIs. [5c3a9ae](https://github.com/ecrespo/fastapi_todos/commit/5c3a9ae)
- Celery integration for asynchronous task processing. [ca00d82](https://github.com/ecrespo/fastapi_todos/commit/ca00d82)
- PostgreSQL support via async SQLAlchemy; compatible with existing SQLite flows. [e1716ae](https://github.com/ecrespo/fastapi_todos/commit/e1716ae)

### Changed
- Refactored Todos endpoints and introduced a centralized Redis caching utility to improve performance. [a9423e9](https://github.com/ecrespo/fastapi_todos/commit/a9423e9)
- Developer tooling: added Makefile for streamlined workflows. [a50b77b](https://github.com/ecrespo/fastapi_todos/commit/a50b77b)

### Fixed
- No user-facing fixes in this release.

### Deprecated
- None.

### Removed
- None.

### Security
- No security-related changes in this release.

---

Legacy history (pre–Keep a Changelog snapshot)

Generated: 2025-10-19 16:47 (local time)

## 2025-10-19
- e1716ae — Add PostgreSQL support and refactor authentication to use async ORM (Ernesto Crespo)
- 26c3fe7 — Add Redis caching support for Todos APIs (Ernesto Crespo)
- 385f202 — Refactor Docker setup and update `.dockerignore` (Ernesto Crespo)
- e0740f7 — Add `.env.example` for environment variable configuration (Ernesto Crespo)
- 4a9895c — Add support for dotenv preload and additional async database drivers (Ernesto Crespo)
- b891026 — Add support for multiple database backends (SQLite, MySQL, PostgreSQL) (Ernesto Crespo)
- docs — Update project-specific development guidelines in README.md (Ernesto Crespo)
- 63d69df — Add `created_at` and `status` columns to `todos` table (Ernesto Crespo)
- 825706e — Add Alembic for database migrations and migrate to SQLAlchemy for async ORM (Ernesto Crespo)
- 5fa5f23 — Add async database connection management (Ernesto Crespo)
- 205efb6 — Add secure headers middleware (Ernesto Crespo)
- a946bc2 — Introduce async database support with aiosqlite and overhaul Todos API (Ernesto Crespo)
- b612852 — Add documentation files (Ernesto Crespo)
- 63002fe — Add rate limiting with SlowAPI (Ernesto Crespo)

## 2025-10-18
- da65af0 — Add infrastructure updates and middleware integration (Ernesto Crespo)
- 2cca2a3 — Add token-based authorization for Todos API (Ernesto Crespo)
- 489854b — Refactor Todos API and logging (Ernesto Crespo)
- eee957e — Introduce shared configurations, database, and services layers (Ernesto Crespo)
- b72cfe7 — Add Todos API implementation with models and endpoints (Ernesto Crespo)
- 9a39eb1 — Add project scaffolding for FastAPI Todos (Ernesto Crespo)
- 0044212 — Initial commit (Ernesto Crespo)

Notes:
- This section reflects an earlier, non–Keep a Changelog style snapshot of commit history.
