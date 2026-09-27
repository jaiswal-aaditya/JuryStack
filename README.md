# JuryStack

JuryStack is a self-hosted hackathon submission and judging portal for DOGFOOD
2026. Its local three-service runtime, migration path, and idempotent official
fixture import are verified. Product workflows and official acceptance routes
remain intentionally unimplemented. Local authentication, opaque sessions,
and backend authorization-policy foundations are also verified.

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

## Current status

T1 and T2 are targets, not current claims. `.dogfood.toml` therefore claims no
tier yet and retains provisional checker routes/auth values for later
implementation. The current generated `acceptance-report.txt` verifies no tier:
the application shell is public, but the fixture gallery and T2 product routes
do not exist yet. Its apparent late-submission pass is an incidental Nginx 405,
not implemented deadline enforcement. See `PLAN.md` for requirement-level
status.

Runtime configuration is local-only and documented in `.env.example`. The
default PostgreSQL credentials are intentionally development credentials and
must be changed for any non-local deployment.

## License

Apache License 2.0. See `LICENSE`.
