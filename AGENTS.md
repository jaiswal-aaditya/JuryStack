# AGENTS.md — JuryStack

## 1. Purpose and authority

This repository is the DOGFOOD 2026 hackathon submission for **JuryStack**, a
self-hosted hackathon submission and judging platform.

Before changing code, read these files completely:

1. `spec.md`
2. `run.py`
3. `fixtures.json`
4. `.dogfood.toml`
5. `PLAN.md`
6. The documentation relevant to the area being changed

Authority order:

1. The official DOGFOOD specification and checker
2. The official fixture data
3. Existing tests and documented product decisions
4. This file
5. The current task or prompt

If instructions conflict, follow the higher authority and record the conflict in
`PLAN.md`. Do not silently reinterpret an official requirement.

The official files do not prescribe a framework, database schema, route naming
scheme, branch strategy, or internal repository layout. This repository's
architecture and conventions are defined below for consistency.

The repository may already contain a partially created folder structure or
implementation. Inspect it before changing anything, preserve compatible work,
and create only what is missing or genuinely conflicting. Do not regenerate the
repository to make it match an example tree cosmetically.

## 2. Time-window rule

DOGFOOD permits planning, reading, schema sketches, and team coordination before
Friday, 25 September 2026 at 18:00 UTC. Project implementation code must be
written only during the 72-hour event window, ending Monday, 28 September 2026
at 18:00 UTC.

Do not create, paste, generate, or adapt application code before kickoff. This
planning document may exist before kickoff, but implementation must wait.

## 3. Product target and priority

Target a complete, defensible T1 and T2 submission. Required lifecycle:

1. Organizer creates and configures an event.
2. Participants form teams and submit projects.
3. The server prevents edits/submissions after the UTC deadline.
4. The public browses and filters the gallery.
5. Organizers invite and assign judges.
6. Judges score only assigned projects and cannot read peer scorecards.
7. Organizers monitor progress, normalize results, and export CSV.

Priority order:

1. Clean offline startup and idempotent fixture seeding
2. Official T1 acceptance checks
3. Real T1 functionality
4. Official T2 acceptance checks and backend authorization
5. Real T2 functionality, normalization, auditability, and documentation
6. Optional bonus work
7. T3/T4 only after every claimed lower tier is complete and verified

Never trade a passing lower tier for an unfinished higher tier. Never claim a
tier that the current build and documentation do not support.

## 4. Required repository boundaries

- Keep all application code written during the event under `src/`.
- Keep the team's tests under root-level `tests/`.
- Keep official `run.py` and `fixtures.json` unchanged at the repository root.
- Keep `.dogfood.toml`, `docker-compose.yml`, required documents, and `LICENSE`
  at the repository root.
- Treat `acceptance-report.txt` as generated output from the official checker;
  never hand-edit it.
- Do not move or rename required root files without confirming the specification.

## 5. Architecture

Use a three-service modular monolith:

- `web`: Nginx serves the compiled React application and proxies `/api` to the
  backend. It is the only service exposed to the host, on port `8080`.
- `api`: FastAPI owns business rules, authentication, authorization, seeding,
  scoring, normalization, CSV export, and the OpenAPI document.
- `db`: PostgreSQL stores all portal data in a local Docker volume.

Request flow:

`browser/checker -> Nginx :8080 -> static React or /api -> FastAPI -> PostgreSQL`

This is one deployable application, not a microservice system. Keep business
logic in backend services, not in route handlers, React components, or Nginx.

### Public gallery and checker compatibility

The official checker is not a browser and does not execute JavaScript. Configure
`routes.gallery` in `.dogfood.toml` to a public backend endpoint such as
`/api/public/projects`, whose raw HTTP response contains fixture project titles.
The human-facing React route may remain `/projects`.

### Backend modules

Organize FastAPI by domain:

- `auth`: login, logout, sessions, current actor
- `events`: event dates, tracks, prizes, custom questions
- `teams`: memberships and invite links
- `projects`: drafts, submissions, gallery, deadline enforcement
- `judging`: invitations, assignments, rubrics, private scorecards
- `results`: aggregation, normalization, ranking, CSV export
- `audit`: append-only human-readable security and workflow events
- `core`: configuration, database access, shared errors, security primitives

Routes validate transport input and call services. Services implement use cases
and policy checks. Repositories contain SQLAlchemy queries. Do not access the
database directly from React or scatter queries across route modules.

### Data model

Use explicit relational tables for:

- `users`
- `sessions`
- `events`
- `tracks`
- `prizes`
- `teams`
- `team_members`
- `team_invites`
- `projects`
- `custom_questions`
- `custom_answers`
- `rubrics`
- `rubric_criteria`
- `judge_invitations`
- `judge_track_eligibility`
- `judge_assignments`
- `scorecards`
- `criterion_scores`
- `audit_events`

Store relationships using stable string IDs. Preserve every official fixture ID
exactly as provided. Store timestamps as timezone-aware UTC datetimes and emit
ISO 8601 UTC values at API boundaries.

Use primary keys, foreign keys, unique constraints, check constraints, and
indexes for integrity and lookup invariants, including session token hashes,
event slugs, invite token hashes, assignment identity, and one logical
scorecard per judge/project/rubric version. Do not impose a
one-project-per-team constraint on imported fixture data: the fixtures contain
41 project records for 40 teams, including two project records for `tm_07`.

Manage every schema change with Alembic. Review generated migrations before
running them, keep migrations forward-applicable from an empty database, and do
not use `Base.metadata.create_all()` as the production migration strategy.

The fixture loader must be idempotent and must preserve awkward records rather
than cleaning them up. Repeated startup must not multiply data.

## 6. Technology decisions

Use the following fixed stack unless an official rule or a documented team
decision changes it:

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Routing: React Router
- Server-state fetching: TanStack Query
- Forms and validation: React Hook Form with Zod
- Backend: Python with FastAPI and Pydantic
- ORM: SQLAlchemy 2 using typed declarative models and async sessions
- Database driver: asyncpg
- Migrations: Alembic
- Database: local PostgreSQL container with a named Docker volume
- Authentication: local email/password plus server-side opaque sessions
- Password hashing: Argon2id through a maintained Python password library
- Edge/static server: Nginx
- Containers: Docker and Docker Compose
- Backend tests: Pytest and HTTPX
- Frontend tests: Vitest and React Testing Library
- Browser smoke tests: Playwright, limited to critical lifecycle paths
- Python quality: Ruff; add static typing checks only if they stay fast/reliable
- TypeScript quality: ESLint and Prettier
- License: MIT unless the team explicitly chooses another OSI-approved license

Commit dependency lockfiles. Pin container image versions; do not use floating
`latest` tags. The running portal must make no network calls and require no
cloud account, API key, hosted database, hosted authentication, external API,
CDN, analytics service, or proprietary runtime.

## 7. Authentication and authorization rules

- Authentication is local. Never introduce OAuth-only login or authentication
  as a service.
- Use opaque session tokens in HttpOnly cookies. Store only token hashes in the
  database for normal sessions.
- Configure `Secure` according to environment; use `SameSite=Lax` at minimum.
- Rotate the session on login and invalidate it on logout.
- Seed deterministic local-only sessions for organizer, `judge_a`, `judge_b`,
  and participant so the checker can attach their headers.
- Print the seeded test headers at startup without printing passwords or
  unrelated secrets.
- Put the same working headers in `.dogfood.toml`.
- Treat seeded tokens as demo-only local credentials, never production secrets.

All authorization is enforced by FastAPI. UI visibility is only a convenience.
Use centralized policies/dependencies for role, ownership, event, assignment,
and track scope. A direct HTTP request must be rejected when the actor lacks
permission.

Critical invariant: a judge may read and edit only their own scorecards for
projects within their assignments. `judge_b` requesting `judge_a`'s scores must
receive exactly `401` or `403`; a participant requesting judge routes must also
receive `401` or `403`.

## 8. Domain rules and edge cases

- Use server time, not browser time, for every deadline decision.
- The fixture event closes at `2026-03-01T18:00:00Z`; a participant submission
  to that event must return a genuine 4xx deadline error.
- Use database transactions for multi-step writes and fixture imports. Keep
  transaction boundaries in services rather than HTTP route handlers.
- Validate and normalize user-controlled URLs.
- Prevent CSV formula injection by prefixing dangerous cells beginning with
  `=`, `+`, `-`, or `@` before export.
- Audit authentication changes, invitations, assignments, submission state
  changes, rubric edits, scorecard submissions, result publication, and exports.
- Audit events are append-only through the application.
- Handle missing score entries, unequal review counts, empty comments,
  incomplete batches, and a zero-variance/constant-scoring judge.
- Do not silently delete, merge, or repair fixture anomalies.

### Scoring and normalization

- Validate rubric weights and score ranges on the backend.
- Calculate weighted raw scores in one backend module with deterministic tests.
- Implement and document one defensible cross-judge normalization method.
- Define explicit fallbacks for constant scorers, one-review judges, missing
  criteria, and insufficient overlap.
- Preserve raw scores. Normalized values are derived data, never destructive
  replacements.
- Keep `JUDGING.md`, implementation, API output, and tests mathematically aligned.

## 9. API conventions

- Prefix application APIs with `/api`.
- Use plural resource names and stable string IDs.
- Use JSON for normal request/response bodies and `text/csv` for exports.
- Return appropriate status codes: `400/422` invalid input, `401` unauthenticated,
  `403` authenticated but forbidden, `404` absent or deliberately undisclosed,
  and `409` state conflict.
- Return one consistent error envelope with a machine-readable code and a safe
  human-readable message.
- Paginate potentially large lists, but ensure the configured checker gallery
  route's first response contains at least one of the first three fixture titles.
- Keep OpenAPI accurate. Every action exposed by the UI must use a documented
  backend endpoint.
- Avoid leaking password hashes, session hashes, invite hashes, private scores,
  internal database IDs, or stack traces.

## 10. Frontend conventions

- Organize by feature, with shared primitives only when genuinely reused.
- Type API contracts. Do not duplicate scoring, deadline, or permission logic in
  the frontend as an authority.
- Every async screen must have loading, empty, error, and success states.
- Use semantic HTML and keyboard-accessible controls.
- Keep styling functional and consistent; passing flows and clarity take priority
  over landing-page polish.
- Never rely on hidden buttons as authorization.

## 11. Coding conventions

### Python

- Use type hints on public functions and service boundaries.
- Keep route handlers thin and async I/O non-blocking.
- Use Pydantic models at API and configuration boundaries.
- Raise domain-specific errors and translate them centrally to HTTP responses.
- Use structured logs; do not log passwords, raw session tokens, or personal
  data unnecessarily.

### TypeScript

- Keep strict mode enabled.
- Avoid `any`; validate untrusted API data at a boundary when practical.
- Use named exports except where framework conventions make a default export
  clearer.
- Keep components focused; move network access into feature API/query modules.

### General

- Prefer the smallest clear implementation over speculative abstraction.
- Do not add a microservice, queue, cache, object store, or third-party service
  unless an existing verified requirement cannot be met without it.
- Do not perform broad rewrites while fixing a narrow issue.
- Never overwrite unrelated work or edit generated/official files casually.
- Document important tradeoffs in an Architecture Decision Record under
  `docs/adr/`.

## 12. Testing and acceptance contract

Every feature change must include or update tests at the lowest useful layer.
Prioritize tests for:

- expired deadline boundaries
- authentication and logout invalidation
- role, ownership, track, and assignment isolation
- judge peer-score denial
- participant denial on judge APIs
- organizer-only CSV export
- idempotent fixture seeding
- preservation of duplicate fixture submissions
- weighted score calculations
- incomplete review data
- zero-variance normalization fallback
- CSV injection handling

The official checker performs these exact behavioral checks:

1. Public gallery returns `200` without authentication.
2. Its raw response body includes a known fixture project title.
3. A participant's late submission returns a `4xx`.
4. `judge_a` can retrieve their own scores with `200`.
5. `judge_b` gets `401` or `403` for `judge_a`'s scores.
6. A participant gets `401` or `403` from the judge scores route.
7. Organizer CSV export returns `200`, and the first response line has a comma.

Run the official checker with:

```bash
python3 run.py .dogfood.toml > acceptance-report.txt
```

Do not modify `run.py` to make the portal pass. Fix the portal or its config.

Before completion, perform a clean-state verification:

```bash
docker compose down -v
docker compose up --build
python3 run.py .dogfood.toml > acceptance-report.txt
```

Then run the repository's backend, frontend, and end-to-end tests. Record exact
commands and outcomes. Commit `acceptance-report.txt` even if it contains honest
failures, and mirror known gaps in `README.md`.

## 13. Agent workflow

For every task, an AI agent must:

1. Read the authoritative files and inspect `git status` before editing.
2. Inspect the existing implementation, tests, and nearby conventions.
3. Identify the smallest vertical slice that satisfies the task.
4. Update `PLAN.md` when requirement status, scope, or assumptions change.
5. Implement backend enforcement before or with UI behavior.
6. Add focused tests, including at least one forbidden/adversarial path for
   security-sensitive changes.
7. Run relevant formatting, linting, type, and test commands.
8. Run the official checker whenever a T1/T2 contract route or its data changes.
9. Report changed files, exact commands, results, assumptions, and remaining gaps.

Agents must not:

- claim success without executing relevant tests
- fabricate test output or acceptance results
- weaken assertions simply to turn failures green
- change `.dogfood.toml` routes without checking the real endpoint and rerunning
  `run.py`
- add optional features while a claimed lower-tier acceptance check is failing
- expose another judge's score data through list, detail, export, logs, or error
  messages
- introduce hosted dependencies or runtime network requirements
- regenerate or "clean" the official fixtures
- hand-edit `acceptance-report.txt`
- commit credentials beyond the intentional local-only seeded checker sessions

If a requirement is ambiguous, make the safest conservative interpretation,
record it, and continue only when it does not risk violating the spec. Escalate
genuine rule ambiguity to the organizers rather than guessing.

## 14. Team ownership and coordination

Suggested ownership areas:

- Backend/core owner: FastAPI, auth, policies, database access, indexes
- Frontend owner: React flows, accessibility, gallery, submissions, dashboards
- Judging owner: assignments, rubric, scorecards, normalization, judging tests
- Integration/QA owner: Docker, Nginx, seeding, checker, docs, clean-state runs

Ownership is not exclusivity, but the owner reviews changes to their boundary.
Only one person at a time should change shared SQLAlchemy models or Alembic
migrations.
Coordinate before editing cross-cutting files such as `docker-compose.yml`,
`.dogfood.toml`, authentication policy, fixture seeding, and shared API contracts.
Merge small working slices frequently and avoid parallel redesigns of the same
files.

## 15. Definition of done

A task is done only when:

- the requested behavior works end to end
- backend authorization and validation are present
- relevant automated tests pass
- affected official acceptance checks pass
- no hosted/runtime dependency was introduced
- documentation and `PLAN.md` reflect the result
- known limitations are stated honestly

The submission is done only when a fresh-volume `docker compose up` produces a
seeded portal at `http://localhost:8080`, all claimed tiers are supported, the
official report is current, required root files exist, the repository is public
under an OSI-approved license, and the five-minute demo shows the full lifecycle.
