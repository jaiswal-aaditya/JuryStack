# ADR 0001: Run migrations and fixture seeding in the API entrypoint

- Status: accepted
- Date: 2026-09-27

## Context

JuryStack must remain a three-service application and start from an empty named
PostgreSQL volume without manual commands. Migrations and fixture import must not
race database initialization, and repeated startup must be safe.

## Decision

Compose waits for the database `pg_isready` health check before starting the API.
The API entrypoint synchronously runs `alembic upgrade head`, performs one
transactional idempotent fixture upsert, and then uses `exec` to start Uvicorn.
Nginx waits for the database-aware API health check.

This keeps migration and seed logic in the FastAPI application image without
adding a fourth service. Concurrent API replicas are out of scope for the local
single-process runtime; a future multi-replica deployment would need a separate
deployment-time migration job or an advisory lock.

## Consequences

- `docker compose up` is sufficient after images exist.
- Failed migration or seeding prevents the API and web services becoming ready.
- Every restart validates migrations and refreshes fixture-backed rows without
  multiplying them.
- Runtime containers need only the local Compose network and make no external
  requests.
