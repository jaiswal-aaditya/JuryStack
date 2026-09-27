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
`judging`, `results`, `audit`, and shared `core`. Routes validate transport data
and call services; services own use cases, policy checks, audits, and transaction
boundaries; repositories own SQLAlchemy queries. Tier 1 uses this split for
event configuration, team invites, project drafts/submission, and the public
gallery. The first Tier 2 slice uses the same split for versioned rubrics,
local judge invitations, track eligibility, and manual or balanced assignment.

## Tier 1 request paths

Public gallery and detail reads query only projects in `submitted` state.
Authenticated participant writes resolve team membership in PostgreSQL before
changing a project. Every create, edit, and submit use case loads the event and
compares server UTC time with its open/close timestamps. Organizer event writes
replace their nested configuration transactionally. Team invite tokens cross
the API boundary once, while only their SHA-256 hashes and expirations persist.

React uses TanStack Query for server state and keeps no authoritative role,
ownership, or deadline decision. Nginx serves browser routes through the SPA
fallback, while `/api` is always proxied to FastAPI, including the raw JSON
gallery used by the official non-browser checker.

## First Tier 2 judging slice

Organizer-only routes create immutable rubric versions, issue local invitation
links, list event judges and assignments, and create or remove assignments.
Invitation links contain a cryptographically random token that crosses the API
boundary only when issued; the database stores its hash, expiry, track scope,
and single-use acceptance marker. Acceptance can create a password-backed local
judge or, after authentication, attach the invited email's existing account.

Balanced assignment planning is deterministic and completes before writes are
made. It counts existing load, excludes duplicate judge/project pairs, and
selects only judges eligible for each project's track; an insufficient track
pool rejects the entire request. Judge project queries independently join both
assignment and current track eligibility, so stale or forged direct requests
cannot widen judge visibility. Rubric, invitation, acceptance, manual
assignment, removal, and balanced-batch writes append readable audit events in
the same transaction.

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
