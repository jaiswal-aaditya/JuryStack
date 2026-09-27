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

## Authentication and authorization

Authentication is entirely local. Passwords are hashed with Argon2id. A
successful email/password login creates a cryptographically random opaque
session token, sends it only as an HttpOnly, SameSite=Lax cookie, and stores
only its SHA-256 hash in PostgreSQL. A successful login deletes any session
presented by the browser before creating the replacement; logout deletes the
server-side session. Cookie `Secure` behavior and the twelve-hour default TTL
are environment settings. Successful login and logout changes append audit rows
without recording passwords or token material.

`visitor` represents the absence of an authenticated user. Stored actors use
the constrained `participant`, `judge`, `organizer`, or `admin` roles. The
four deterministic local checker cookies remain ordinary server-side session
records, mapped to the organizer, `jdg_01`, `jdg_02`, and the first fixture
participant respectively.

FastAPI dependencies resolve the current actor and enforce required roles.
The authorization service provides reusable ownership, event-membership,
track-eligibility, and judge-assignment checks. Organizer/admin overrides are
explicit rather than implicit. Missing or invalid sessions produce `401`;
authenticated actors outside a policy scope receive `403`. React consumes
`/api/auth/me` only to improve navigation and never acts as the authorization
boundary.

The migration-and-seed startup decision is recorded under `docs/adr/`.
