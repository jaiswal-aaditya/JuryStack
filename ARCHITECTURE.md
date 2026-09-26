# Architecture

JuryStack is a three-service modular monolith. Nginx is the only host-facing
service on port 8080, serving the React build and forwarding `/api` to FastAPI.
FastAPI owns validation, authentication, authorization, transactions, scoring,
exports, fixture loading, and OpenAPI. PostgreSQL is the only persistent store.

Compose starts PostgreSQL first and waits for `pg_isready`. The API entrypoint
then runs `alembic upgrade head`, performs the idempotent fixture import in one
transaction, and finally replaces itself with Uvicorn. API health returns 200
only when the migrated `events` table contains seeded data. Nginx waits for that
health check before starting and never sends `/api` paths through the SPA
fallback.

Only Nginx publishes a host port (`8080`). The API and PostgreSQL ports exist
only on the Compose network. The frontend build contains all browser assets, so
running containers make no internet requests and require no external accounts.

Backend packages are divided into `auth`, `events`, `teams`, `projects`,
`judging`, `results`, `audit`, and shared `core`. Future routes should validate
transport data and call services; services own use cases and transaction
boundaries; repositories own SQLAlchemy queries.

The migration-and-seed startup decision is recorded under `docs/adr/`.
