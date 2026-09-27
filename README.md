# JuryStack

JuryStack is a self-hosted hackathon submission and judging portal for DOGFOOD
2026. Tier 1 is implemented end to end: organizers configure events,
participants form teams and submit projects before a server-enforced UTC
deadline, and visitors browse a searchable, filterable public gallery. Tier 2
rubric, invitation, assignment, and private-scorecard slices are implemented,
but Tier 2 remains unclaimed until results normalization and CSV export exist.

## Architecture

The deployable application has three local services:

- `web`: Nginx serving the compiled React application and proxying `/api`.
- `api`: FastAPI modular monolith containing all application policy.
- `db`: PostgreSQL with a named local volume.

No runtime cloud service, hosted account, or external API is required.

## Local runtime

Copy `.env.example` to `.env` only when overriding the safe local defaults.
Build and start the complete portal, recreating any container that still points
at an older local image, with:

```bash
docker compose up --build --force-recreate
```

The shorter official command remains sufficient when the source tree has not
changed:

```bash
docker compose up
```

If a previous interrupted build left stale Docker cache, perform one guaranteed
clean image rebuild:

```bash
docker compose build --no-cache
docker compose up --force-recreate
```

The Nginx application route sends `Cache-Control: no-store`, so a normal browser
refresh after the recreated `web` container starts loads the current frontend
bundle rather than an older cached shell.

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

## Judging flows

- Organizers configure versioned rubrics, invite local judges, and manage
  track-safe assignments at `/organizer/judging`.
- Judges open `/judge/assignments`, select an assigned project, save partial
  private scorecard drafts, and explicitly submit a complete scorecard.
- Submitted scorecards are read-only. Judges cannot list or retrieve peer
  scorecards; organizer score and progress inspection uses separate APIs.

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
all official T1 checks plus the three judge-isolation probes: judge A reads
their own scores, judge B receives `403` when requesting judge A, and the
participant receives `403`. The organizer CSV check remains the sole official
T2 failure, so T2 is not yet claimed.

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
