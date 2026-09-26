# JuryStack implementation plan

Status vocabulary: **scaffolded** means the module/page/test location exists but
contains no product behavior; **not started** means no implementation or proof
exists; **verified** is reserved for behavior exercised successfully.

## T1/T2 requirements traceability

| Tier / requirement | Backend module / endpoint | Frontend page | PostgreSQL migration / constraint | Test | Status |
|---|---|---|---|---|---|
| T1 local login, logout, current actor, opaque sessions | `auth`; `/api/auth/login`, `/logout`, `/me` | `/login`, account menu | `users`, `sessions`; unique token hash and expiry index | `tests/backend/auth/`; frontend auth tests | Scaffolded |
| T1 organizer creates/configures event | `events`; `/api/events` | `/organizer/events/*` | `events`; unique slug, UTC date checks | event service/API tests | Scaffolded |
| T1 tracks, prizes, custom questions | `events`; nested event resources | event setup pages | `tracks`, `prizes`, `custom_questions`; event FKs/order constraints | event configuration tests | Scaffolded |
| T1 form and manage teams/invites | `teams`; `/api/teams`, `/invites` | `/teams/*` | `teams`, `team_members`, `team_invites`; membership/invite uniqueness | team ownership and invite tests | Scaffolded |
| T1 project draft/create/edit | `projects`; `/api/projects` | `/projects/new`, `/projects/:id/edit` | `projects`, `custom_answers`; ownership/FK/URL checks | project service/API/form tests | Scaffolded |
| T1 server-side UTC deadline enforcement | `projects` submission service | submission status messaging | event close timestamp; transactional state update | deadline boundary + adversarial direct HTTP tests | Not started |
| T1 public browsable/filterable gallery | `projects`; `/api/public/projects` | `/projects` | project publication/status indexes | public/filter/pagination tests | Scaffolded |
| T1 fixture import is idempotent and exact | `core` seed command/service | n/a | all fixture-backed tables; stable IDs, conflict-safe import | repeated seed + fixture anomaly tests | Not started |
| T1 offline `docker compose up` | process startup/migrations/seeding | Nginx application shell | named PostgreSQL volume + Alembic | clean-volume startup smoke | Scaffolded |
| **run.py 1: public gallery returns 200 unauthenticated** | `GET /api/public/projects` (planned `.dogfood.toml` route) | `/projects` | `projects` publication index | official `run.py`: “gallery is public” | Not started |
| **run.py 2: raw gallery includes a first-three fixture title** | `GET /api/public/projects` | `/projects` | fixture projects, preserving titles | official `run.py`: “project from fixtures shown” | Not started |
| **run.py 3: participant late submission returns 4xx** | `POST /api/projects` (planned) | `/projects/new` | event close time + project state | official `run.py`: “closed event refuses submissions” | Not started |
| T2 invite judges and track eligibility | `judging`; `/api/judge-invitations` | `/organizer/judges` | `judge_invitations`, `judge_track_eligibility`; token hash/uniqueness | invitation and track-scope tests | Scaffolded |
| T2 assign judges to projects | `judging`; `/api/judge-assignments` | `/organizer/assignments` | `judge_assignments`; unique judge/project identity | assignment authorization tests | Scaffolded |
| T2 weighted versioned rubric | `judging`; `/api/rubrics` | `/organizer/rubric` | `rubrics`, `rubric_criteria`; weight/range/version checks | weight/range/version tests | Scaffolded |
| T2 private judge scorecards | `judging`; `/api/judge/scorecards` | `/judge/projects/:id` | `scorecards`, `criterion_scores`; one logical card per judge/project/version | own/peer/participant and assignment isolation tests | Scaffolded |
| T2 organizer progress view | `judging`; `/api/organizer/judging-progress` | `/organizer/progress` | assignment/scorecard lookup indexes | missing/incomplete/unequal-review tests | Scaffolded |
| T2 weighted scoring and normalization | `results`; `/api/results` | `/organizer/results` | raw score preservation; derived result query/materialization TBD | deterministic raw, overlap, one-review, constant-scorer tests | Scaffolded |
| T2 organizer CSV export with formula safety | `results`; `/api/results.csv` | results export control | score/project lookup indexes; append-only export audit | organizer-only + CSV injection tests | Scaffolded |
| T2 audit-sensitive actions | `audit` service | organizer audit page (post-T2 core) | `audit_events`; append-only application policy/indexes | audit creation/immutability tests | Scaffolded |
| **run.py 4: judge A reads own scores with 200** | `GET /api/judge/scorecards` | judge dashboard | assignments/scorecards/criterion scores | official `run.py`: “judge sees own scores” | Not started |
| **run.py 5: judge B gets 401/403 for judge A scores** | `GET /api/judge/scorecards?judge=jdg_01` (planned peer route) | no peer-score UI | centralized actor/scorecard policy | official `run.py`: “judge cannot see peer scores” | Not started |
| **run.py 6: participant gets 401/403 on judge scores** | `GET /api/judge/scorecards` | no participant judge UI | centralized role policy | official `run.py`: “participant blocked” | Not started |
| **run.py 7: organizer CSV is 200 with comma in first line** | `GET /api/results.csv` | results export control | result inputs + export audit | official `run.py`: “csv export works” | Not started |

## Scaffold milestone (2026-09-26)

- Confirmed authoritative fixture shape: 8 tracks, 30 judges, 40 teams, 41
  projects, and 126 score rows. `tm_07` owns `prj_07` and `prj_41`; review
  counts range from 2 to 5; `jdg_07` is a constant scorer; 51 comments are
  empty; submissions close at `2026-03-01T18:00:00Z`.
- Reused the existing React/Vite/Tailwind and FastAPI roots. Replaced the
  conflicting Oxlint choice with the required ESLint/Prettier scaffold and
  aligned Python/container versions. Preserved the existing Apache-2.0 license.
- Added module, migration, test, Nginx, Docker, and documentation scaffolds.
- Product endpoints, database tables, migrations, fixtures, and authentication
  remain unimplemented. `.dogfood.toml` honestly claims no tier; its routes and
  auth values remain provisional until their vertical slices are verified.
- Scaffold verification passed for Ruff, Pytest (1 test), ESLint, Prettier,
  Vitest (1 test), TypeScript, and the Vite production build. Direct startup
  checks returned HTTP 200 from FastAPI `/api/health` and served the compiled
  frontend through Vite preview.
- Environment blockers: this host has neither the Docker Compose v2 plugin nor
  legacy `docker-compose`, so Compose validation/build was not runnable. The
  Playwright smoke test reaches Chromium launch but the host lacks `libnspr4`;
  `playwright install-deps chromium` could not proceed because host `sudo`
  requires an interactive password. These are scaffold verification gaps, not
  product completion claims.

## Next vertical slice

Create and review the initial relational migration, implement idempotent fixture
loading, then expose the public gallery endpoint and run official checks 1–2.
