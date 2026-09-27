# JuryStack

JuryStack is a self-hosted hackathon submission and judging portal for DOGFOOD
2026. Tier 1 is implemented end to end: organizers configure events,
participants form teams and submit projects before a server-enforced UTC
deadline, and visitors browse a searchable, filterable public gallery. Tier 2
is intentionally not started or claimed.

## Architecture

The deployable application has three local services:

- `web`: Nginx serving the compiled React application and proxying `/api`.
- `api`: FastAPI modular monolith containing all application policy.
- `db`: PostgreSQL with a named local volume.

No runtime cloud service, hosted account, or external API is required.

## Local runtime

Copy `.env.example` to `.env` only when overriding the safe local defaults.
Build and start the complete portal with:

```bash
docker compose up --build
```

After the images exist, the official command is sufficient:

```bash
docker compose up
```

The API container waits for PostgreSQL readiness, applies Alembic migrations,
and transactionally upserts `fixtures.json` before starting FastAPI. Open
`http://localhost:8080`; only Nginx publishes a host port. Readiness is exposed
through Nginx at `http://localhost:8080/api/health`.

The local login page is `http://localhost:8080/login`. Seeded fixture users use
the intentionally local-only demo password `jurystack-local-demo`; the checker
continues to use the deterministic Cookie headers printed during API startup.
Do not reuse these credentials outside local development.

## Tier 1 flows

- Browse submitted projects at `/`, search by project or team text, filter by
  track, and open public project details without signing in.
- Participants use `/workspace` to create a team, issue an expiring single-use
  invite, accept an invite, and manage drafts. Drafts support event-specific
  questions and can be submitted once complete.
- Organizers use `/organizer/events` to create or edit UTC dates, tracks,
  prizes, and custom submission questions.
- Project creation, edits, and submission are checked against the event window
  using server UTC time. At or after closing, a direct request returns
  `409 deadline_closed`.

The fixture event is deliberately closed. To exercise the open-event path,
create a future event as the organizer, then log in as a participant and form a
team for it.

Reset to a completely empty local database with:

```bash
docker compose down --volumes
```

## Direct development

Backend:

```bash
cd src/backend
uv sync --locked --all-groups
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd src/frontend
pnpm install --frozen-lockfile
pnpm dev
```

## Verification status

`.dogfood.toml` claims only T1. The generated `acceptance-report.txt` verifies
all official T1 checks: the unauthenticated gallery returns `200`, fixture
titles appear in its raw response, and the closed fixture event rejects the
participant's direct project POST with a genuine deadline conflict. T2 routes
remain absent and the checker reports their expected failures.

Backend unit and live API checks, frontend lint/type/build/tests, pristine
PostgreSQL fixture verification, Alembic drift checking, and the complete live
Tier 1 lifecycle pass. The Playwright scenario is present, but this host cannot
launch Chromium because `libnspr4.so` is unavailable; it remains runnable on a
host with Playwright's operating-system dependencies installed.

The latest strict acceptance review repeated the build from a deleted volume,
inspected the seed and request logs, independently probed the gallery, deadline,
cookie mapping, and Nginx API boundary, and regenerated the report exclusively
through `run.py`. No T1 failure or corrective product change was found.

Runtime configuration is local-only and documented in `.env.example`. The
default PostgreSQL credentials are intentionally development credentials and
must be changed for any non-local deployment.

## License

Apache License 2.0. See `LICENSE`.
