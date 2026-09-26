# JuryStack

JuryStack is a self-hosted hackathon submission and judging portal for DOGFOOD
2026. The repository is currently at the verified scaffold milestone: the
FastAPI and React applications build independently, while product workflows and
the official acceptance routes remain intentionally unimplemented.

## Architecture

The deployable application has three local services:

- `web`: Nginx serving the compiled React application and proxying `/api`.
- `api`: FastAPI modular monolith containing all application policy.
- `db`: PostgreSQL with a named local volume.

No runtime cloud service, hosted account, or external API is required.

## Development

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

The full stack will be started with `docker compose up --build` once fixture
seeding and database migrations are implemented.

## Current status

T1 and T2 are targets, not current claims. `.dogfood.toml` therefore claims no
tier yet and retains provisional checker routes/auth values for later
implementation. No `acceptance-report.txt` is generated during this
scaffold-only phase because the checker-facing product endpoints do not exist
yet. See `PLAN.md` for requirement-level status.

## License

Apache License 2.0. See `LICENSE`.
