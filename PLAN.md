# JuryStack implementation plan

Status vocabulary: **scaffolded** means the module/page/test location exists but
contains no product behavior; **not started** means no implementation or proof
exists; **verified** is reserved for behavior exercised successfully.

## T1/T2 requirements traceability

| Tier / requirement | Backend module / endpoint | Frontend page | PostgreSQL migration / constraint | Test | Status |
|---|---|---|---|---|---|
| T1 local login, logout, current actor, opaque sessions | `auth`; `/api/auth/login`, `/logout`, `/me`; reusable role/owner/event/track/assignment policies | `/login`, account menu | `users`, `sessions`; role check, unique token hash and expiry index | `test_auth.py`; `auth.test.tsx`; live rotation/logout checks | Verified |
| T1 organizer creates/configures event | `events`; `/api/events` | `/organizer/events` | `events`; unique slug and aware ordered UTC dates | schema and live create/edit tests | Verified |
| T1 tracks, prizes, custom questions | `events`; nested configuration | event configuration form | `tracks`, `prizes`, `custom_questions`; event FKs/order constraints | live nested configuration test | Verified |
| T1 form and manage teams/invites | `teams`; `/api/teams`, `/team-invites` | `/workspace` | `teams`, `team_members`, `team_invites`; membership/hash uniqueness | live nonmember/reuse/accept tests | Verified |
| T1 project draft/create/edit | `projects`; `/api/projects` | `/workspace/projects/new`, edit route | `projects`, `custom_answers`; ownership/FK/URL checks | live ownership/custom-answer lifecycle | Verified |
| T1 server-side UTC deadline enforcement | `projects` service | deadline-closed form state | event open/close timestamps; transactional state update | exact boundary and direct late HTTP tests | Verified |
| T1 public browsable/filterable gallery | `projects`; `/api/public/projects` | `/`, `/projects/:id` | project status/event-track indexes | live public/detail/search/filter tests | Verified |
| T1 fixture import is idempotent and exact | `core.fixtures`, `core.seed` startup command | n/a | all fixture-backed tables; stable string IDs, FKs, association tables, conflict-no-op transactional import | `test_seed.py`; live `test_database_integration.py`; two-start count check | Verified |
| T1 offline `docker compose up` | process startup/migrations/seeding | Nginx application shell | named PostgreSQL volume + Alembic | clean-volume startup smoke | Verified |
| **run.py 1: public gallery returns 200 unauthenticated** | `GET /api/public/projects` | `/` | `projects` publication index | official `run.py`: “gallery is public” | Verified |
| **run.py 2: raw gallery includes a first-three fixture title** | `GET /api/public/projects` | `/` | fixture projects, preserving titles | official `run.py`: “project from fixtures shown” | Verified |
| **run.py 3: participant late submission returns 4xx** | `POST /api/projects` | project editor | event close time + project state | official `run.py`: “closed event refuses submissions” | Verified |
| T2 invite judges and track eligibility | `judging`; `/api/judge-invitations` | `/organizer/judges` | `judge_invitations`, `judge_track_eligibility`; token hash/uniqueness | invitation and track-scope tests | Scaffolded |
| T2 assign judges to projects | `judging`; `/api/judge-assignments` | `/organizer/assignments` | `judge_assignments`; unique judge/project identity | assignment authorization tests | Scaffolded |
| T2 weighted versioned rubric | `judging`; `/api/rubrics` | `/organizer/rubric` | `rubrics`, `rubric_criteria`; weight/range/version checks | weight/range/version tests | Scaffolded |
| T2 private judge scorecards | `judging`; `/api/judge/scorecards` | `/judge/projects/:id` | `scorecards`, `criterion_scores`; one logical card per judge/project/version | own/peer/participant and assignment isolation tests | Scaffolded |
| T2 organizer progress view | `judging`; `/api/organizer/judging-progress` | `/organizer/progress` | assignment/scorecard lookup indexes | missing/incomplete/unequal-review tests | Scaffolded |
| T2 weighted scoring and normalization | `results`; `/api/results` | `/organizer/results` | raw score preservation; derived result query/materialization TBD | deterministic raw, overlap, one-review, constant-scorer tests | Scaffolded |
| T2 organizer CSV export with formula safety | `results`; `/api/results.csv` | results export control | score/project lookup indexes; append-only export audit | organizer-only + CSV injection tests | Scaffolded |
| T2 audit-sensitive actions | `audit` service | organizer audit page (post-T2 core) | `audit_events`; append-only application policy/indexes | audit creation/immutability tests | Scaffolded |
| **run.py 4: judge A reads own scores with 200** | `GET /api/judge/scores` | judge dashboard | assignments/scorecards/criterion scores | official `run.py`: “judge sees own scores” | Not started |
| **run.py 5: judge B gets 401/403 for judge A scores** | `GET /api/judge/scores?judge_id=jdg_01` | no peer-score UI | centralized actor/scorecard policy | official `run.py`: “judge cannot see peer scores” | Not started |
| **run.py 6: participant gets 401/403 on judge scores** | `GET /api/judge/scores` | no participant judge UI | centralized role policy | official `run.py`: “participant blocked” | Not started |
| **run.py 7: organizer CSV is 200 with comma in first line** | `GET /api/organizer/results.csv` | results export control | result inputs + export audit | official `run.py`: “csv export works” | Not started |

## Scaffold milestone (2026-09-26)

- Confirmed authoritative fixture shape: 8 tracks, 30 judges, 40 teams, 41
  projects, and 126 score rows. `tm_07` owns `prj_07` and `prj_41`; review
  counts range from 2 to 5; `jdg_07` is a constant scorer; 51 comments are
  empty; submissions close at `2026-03-01T18:00:00Z`.
- Reused the existing React/Vite/Tailwind and FastAPI roots. Replaced the
  conflicting Oxlint choice with the required ESLint/Prettier scaffold and
  aligned Python/container versions. Preserved the existing Apache-2.0 license.
- Added module, migration, test, Nginx, Docker, and documentation scaffolds.
- At this scaffold milestone, product endpoints, database tables, migrations,
  fixtures, and authentication were unimplemented. The database runtime was
  subsequently completed in the milestone below.
- Scaffold verification passed for Ruff, Pytest (1 test), ESLint, Prettier,
  Vitest (1 test), TypeScript, and the Vite production build. Direct startup
  checks returned HTTP 200 from FastAPI `/api/health` and served the compiled
  frontend through Vite preview.
- The earlier Compose tooling gap was resolved on 2026-09-27. Playwright still
  cannot launch Chromium on this host because `libnspr4` installation requires
  an interactive `sudo` password; this does not affect the container runtime.

## Next vertical slice

Tier 1 is complete. Stop here; begin Tier 2 only under a separate explicit task.

## Authentication foundation milestone (2026-09-27)

- Added local email/password login with Argon2id, random opaque HttpOnly
  cookies, hash-only server-side session storage, login rotation, logout
  invalidation, `/api/auth/me`, and transactional login/logout audit rows. API
  schemas cannot accept a requested role and never serialize credential hashes
  or tokens.
- Added the visitor/participant/judge/organizer/admin role vocabulary, database
  constraints for stored roles, and reusable dependencies/services for role,
  ownership, event, track, and judge-assignment scope. Backend policy is the
  security boundary; frontend state is display-only.
- Preserved all four deterministic checker sessions. Live checks returned 200
  for each; normal login rotation returned 401 for the old cookie and 200 for
  the replacement, and logout changed that replacement to 401.
- Added adversarial backend coverage for missing/invalid authentication, role
  escalation input, participant/judge boundary violations, owned-resource
  isolation, session rotation, and invalidation. Backend tests passed 14 with
  one environment-gated PostgreSQL test; the same database integrity test had
  already passed in-container.
- Added a minimal React login page and account menu backed by TanStack Query,
  React Hook Form, and Zod. Frontend lint, two Vitest tests, TypeScript, and the
  production build pass.

## Relational fixture milestone (2026-09-27)

- Completed typed SQLAlchemy 2 relationships across all normalized tables and
  added reverse-lookup indexes for team membership, track eligibility, project
  assignments, and criterion scores. The reviewed initial migration remains
  forward-applicable from an empty PostgreSQL database and `alembic check`
  reports no drift.
- Changed fixture conflict handling to immutable conflict-no-op inserts within
  one transaction. Automatic startup order remains PostgreSQL health, Alembic
  upgrade, fixture seed, then API launch.
- Added live database coverage for migration revision, validated foreign keys,
  exact fixture IDs/timestamps/scores/comments, actor/session mappings, official
  counts, duplicate `tm_07` projects, review-count anomalies, and `jdg_07`'s
  constant scores.
- A clean first start and a second start against the same named volume both
  produced `8|30|40|41|126|378|4` for tracks, judges, teams, projects,
  scorecards, criterion scores, and sessions. The live integrity test passed
  after both starts.
- `.dogfood.toml` now uses the agreed `/api/public/projects`, `/api/projects`,
  `/api/judge/scores`, peer query, and organizer CSV paths with deterministic
  local cookie headers. These product endpoints remain deliberately
  unimplemented in this data-model phase.

## Local runtime milestone (2026-09-27)

- Added reviewed Alembic revision `20260927_0001` for all required relational
  tables and verified it has no drift from SQLAlchemy metadata.
- Added strict fixture validation and a transactional PostgreSQL upsert. Clean
  and repeated starts preserve 41 projects, 126 scorecards, 378 criterion
  scores, one seed audit event, four demo sessions, and both `tm_07` projects.
- Verified clean `docker compose up --build`, subsequent literal
  `docker compose up`, the React application through Nginx, database-aware
  `/api/health`, API 404 proxying, and exclusive host exposure on port 8080.
- Regenerated the official report. It verifies no tier: the fixture-title and
  T2 routes fail as expected. The late-submission check's 4xx is an incidental
  Nginx method rejection, not deadline enforcement, so that requirement remains
  not started.
- T1/T2 product routes remain unimplemented and no tier is claimed.

## Tier 1 vertical-slice milestone (2026-09-27)

- Added organizer-only event creation and editing for aware UTC dates, tracks,
  prizes, and ordered required/optional custom questions. Alembic revision
  `20260927_0003` adds optional event-start and submission-open timestamps.
- Added participant team creation, membership-backed authorization, and
  expiring single-use invite tokens stored only as hashes. Nonmembers cannot
  issue invites and consumed tokens cannot be reused.
- Added team-owned project drafts, custom answers, submission state and server
  timestamps, URL and event/track validation, and server-side window checks on
  create, edit, and submit. The close instant is exclusive: `now >= close`
  returns `409 deadline_closed` before the checker's sparse late payload can be
  rejected for an unrelated missing field.
- Added the public raw-JSON gallery and detail routes plus search and track
  filters. The React application now provides gallery/detail, team/invite,
  draft/edit/submit, event configuration, and explicit loading, empty, error,
  forbidden, validation, and deadline-closed states.
- Focused tests cover invalid dates, exact open/close boundaries, cross-team
  edits, nonmember invite issuance, invite reuse, required and persisted custom
  answers, late direct requests, and gallery visibility/search/filtering.
- Clean-volume Docker startup, pristine database integrity, Alembic drift,
  backend tests, frontend lint/build/tests, live API lifecycle, and all official
  T1 checks pass. Playwright cannot launch on this host because `libnspr4.so` is
  unavailable; the scenario and Chromium download are otherwise present.
- `.dogfood.toml` now claims T1 only. Tier 2 remains unimplemented and its four
  checker probes honestly return `404`.
