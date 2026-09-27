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
| T2 invite judges and track eligibility | `judging`; `/api/judge-invitations` | `/organizer/judging`, local acceptance link | `judge_invitations`, `judge_invitation_tracks`, `judge_track_eligibility`; unique hash, expiry, row-locked single use | expiry/reuse and live acceptance/track-scope tests | Verified |
| T2 assign judges to projects | `judging`; `/api/judge-assignments`, event list/balance routes, `/api/judge/projects` | `/organizer/judging`, `/judge/assignments` | `judge_assignments`; unique judge/project identity | duplicate, track, unauthorized, visibility, deterministic balance and insufficient-pool tests | Verified |
| T2 weighted versioned rubric | `judging`; event rubric list/create routes | `/organizer/judging` | `rubrics`, `rubric_criteria`; positive relative weight, range, order, and event-version checks | weight/range/label/version history tests | Verified |
| T2 private judge scorecards | `judging`; `/api/judge/scores`, `/api/judge/scorecards`, assigned-project workspace/save/submit routes | `/judge/assignments`, `/judge/projects/:id/score` | `scorecards`, `criterion_scores`; unique judge/project/rubric identity and constrained draft/submitted state | range/completeness, own/peer/participant, guessed-ID, unassigned, track, query-tampering, and submitted-lock tests | Verified |
| T2 organizer progress view | `results`; `/api/organizer/events/{event_id}/progress` | `/organizer/operations` | assignment/scorecard lookup indexes | progress counts, incomplete data, filters, coverage, frontend view | Verified |
| T2 weighted scoring and normalization | `results`; `/api/results` | `/organizer/results` | raw score preservation; derived result query/materialization TBD | deterministic raw, overlap, one-review, constant-scorer tests | Scaffolded |
| T2 organizer CSV export with formula safety | `results`; `/api/organizer/results.csv` | `/organizer/operations` export control | derived score/project joins; append-only export audit | organizer-only, valid parsing, stable fields, incomplete data, formula injection | Verified |
| T2 audit-sensitive actions | `audit`; `/api/organizer/audit-events`; publication endpoint | `/organizer/operations` | `audit_events`; database update/delete rejection; `events.results_published_at` | workflow events, export/publication audit, organizer-only filtered reads | Verified |
| **run.py 4: judge A reads own scores with 200** | `GET /api/judge/scores` | judge assignments and scorecard editor | assignment/eligibility-scoped scorecards | official `run.py`: “judge sees own scores” | Verified |
| **run.py 5: judge B gets 401/403 for judge A scores** | `GET /api/judge/scores?judge_id=jdg_01` | no peer-score UI or preload | authenticated actor equality before query | official `run.py`: “judge cannot see peer scores” | Verified |
| **run.py 6: participant gets 401/403 on judge scores** | `GET /api/judge/scores` | no participant judge UI | centralized judge role policy | official `run.py`: “participant blocked” | Verified |
| **run.py 7: organizer CSV is 200 with comma in first line** | `GET /api/organizer/results.csv` | operations export control | result inputs + export audit | official `run.py`: “csv export works” | Verified |

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

Organizer operations, raw weighted scoring, CSV export, and append-only audit
history are complete. Cross-judge normalization remains the only known Tier 2
product gap, so Tier 2 remains honestly unclaimed.

## Tier 2 operations milestone (2026-09-27)

- Added organizer progress summaries and assignment rows with track, judge,
  project, and completion-state filters plus explicit insufficient-coverage
  reporting against a configurable review target.
- Added organizer-only CSV export with stable event/project/team/track,
  assignment/judge/scorecard/rubric IDs, status and review-count fields, raw
  weighted averages, standards-compliant CSV generation, and formula-prefix
  neutralization.
- Added filtered organizer audit history, auditable CSV export and results
  publication, and a database trigger that rejects audit updates/deletes.
- Added backend and frontend coverage for calculations, incomplete scores,
  CSV parsing/safety, authorization, filters, coverage, export, and audit UI.
- Normalization remains outside this slice; `.dogfood.toml` therefore continues
  to claim T1 only despite all official behavioral probes now passing.

## Frontend UI/UX modernization milestone (2026-09-27)

- Replaced the dark-only prototype shell with a restrained blue design system,
  responsive role-aware navigation, the provided logo and HTML wordmark, and
  light/dark/system themes. System is the default; explicit browser preferences
  persist locally, and an inline pre-render resolver avoids a wrong-theme flash.
- Added real, API-backed role dashboards for participants, judges, organizers,
  and admins, plus a read-only profile surface using only `/api/auth/me` data.
  Navigation exposes only implemented pages appropriate to the current role.
- Redesigned the public gallery, login, participant workspace, judge invitation,
  assignments, organizer judging setup, and private scorecard workflow with
  consistent inputs, status badges, loading/empty/error states, responsive
  layouts, clearer focus states, and reduced-motion support.
- The final precision pass adds contract-safe gallery skeletons, searchable
  project/team controls, track pill filters, project metadata panels, native SVG
  password controls, role-ring avatars, copyable single-use invite links, and
  client-side assignment filtering without changing query keys or API calls.
- Follow-up polish moves the System/Light/Dark control into the global header
  for anonymous and authenticated users, removes the duplicate account-menu
  control, adopts neutral slate/zinc surfaces with a calmer indigo accent,
  integrates the official platform definition into the gallery/login/footer,
  adds `/` search focus and clear behavior, counted track pills, copied-state
  invite buttons, and richer assignment metadata/actions.
- Added password visibility controls and retained the only supported account
  creation path: a secure single-use judge invitation. There is no public or
  administrator account-creation API, so no fake signup route or client-side
  role grant was added.
- Added an accessible final-evaluation confirmation dialog, criterion progress,
  explicit draft/submitted/read-only states, and duplicate-submit prevention.
  The underlying draft and submit endpoints and scoring behavior are unchanged.
- No backend, migration, auth, authorization, checker route, fixture, Docker, or
  request/response contract changed. Frontend tests now cover theme preference
  persistence and final scorecard confirmation in addition to existing flows.
- Verification: frontend ESLint and Prettier passed; Vitest passed 7 tests;
  TypeScript/Vite production build passed; backend Pytest passed 25 with 5
  expected environment-gated skips. After `docker compose down -v` and a clean
  `docker compose up --build -d`, all 4 live Tier 1/judging/scorecard tests
  passed. The official checker still verifies T1 plus all three judge-isolation
  probes; the deliberately deferred CSV check remains `404`, so T2 remains
  unclaimed. Playwright still cannot launch on this host because `libnspr4.so`
  is unavailable.

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

## Strict T1 acceptance review (2026-09-27)

- Repeated `docker compose down -v` followed by literal
  `docker compose up --build`; all three services became healthy and the API
  logs showed migrations from empty followed by the exact official fixture
  counts and checker cookies.
- Independently verified that `/api/public/projects` is unauthenticated JSON
  containing first-three fixture titles, the stored fixture close is still
  `2026-03-01T18:00:00Z`, `prt_2e88` maps to the first fixture participant,
  the official late POST returns `409 deadline_closed`, and unknown `/api`
  paths return backend JSON rather than the React SPA.
- The pristine PostgreSQL integrity test passed. Backend Ruff passed; backend
  tests passed 19 with three environment-gated skips, followed by both live T1
  tests passing against Docker. Frontend lint, formatting, build, and two
  Vitest suites passed.
- Regenerated `acceptance-report.txt` only with the prescribed `run.py` output
  redirection. All T1 lines pass. No product fix was required and no Tier 2
  work was added or claimed.

## First Tier 2 judging slice milestone (2026-09-27)

- Added organizer-created immutable rubric versions with ordered labels,
  descriptions, configurable 0–100 score bounds, and positive relative
  weights. Earlier scorecards remain attached to their original rubric.
- Added local expiring, hash-only, row-locked single-use judge invitations,
  explicit invitation track scope, local account creation/acceptance, and
  invitation creation/acceptance audit events.
- Added organizer inspection, manual assignment/removal, deterministic balanced
  batches, unique-pair enforcement, submitted-project and track checks, and a
  judge view restricted by both assignment and current eligibility. Assignment
  writes are audited transactionally.
- Added organizer and judge React flows with loading, empty, validation,
  forbidden, error, and success states. Focused tests cover invitation expiry
  and reuse, invalid rubrics, duplicates, track violations, unauthorized
  changes, judge visibility, even load, insufficient pools, batch creation, and
  idempotent balancing.
- Normalization, scorecard entry, judging progress, results, and CSV export were
  not implemented in this slice. `.dogfood.toml` therefore continues to claim
  only T1.

## Private scorecard and judge-isolation milestone (2026-09-27)

- Added assignment-and-current-track-scoped judge scorecard list, workspace,
  detail, draft-save, and explicit-submit endpoints. Drafts may be partial;
  submission requires every criterion and locks the card from later edits.
- Enforced criterion identity and configured score bounds in the service, one
  logical judge/project/rubric scorecard in PostgreSQL, and consistent
  draft/submitted timestamp state through Alembic revision `20260927_0005`.
- Added separate organizer-authorized raw scorecard and judging-progress
  endpoints. Judge routes never accept organizer override and never serialize
  peer data; peer detail guesses are deliberately undisclosed as `404`.
- Added a judge scoring page for criterion inputs, private comments, partial
  draft saving, explicit submission, and read-only submitted state. It calls
  only actor-scoped judge endpoints and preloads no peer scores.
- Adversarial live coverage includes changed `judge_id`, guessed peer card IDs,
  an unassigned same-track project, another track, peer detail/list access,
  participant list/detail/write access, invalid ranges, incomplete submission,
  duplicate logical saves, submitted-card edits, and organizer-only inspection.
- The official judge-own, peer-denial, and participant-denial probes now pass.
  CSV export remains unimplemented, so `.dogfood.toml` still claims only T1.
- Final verification rebuilt from a deleted Compose volume: migration/fixture
  integration and Alembic drift checks passed, backend tests passed 25 with 5
  environment-gated skips, all 4 live judging/Tier 1 tests passed, and all 5
  frontend tests plus lint, formatting, and production build passed. The
  official report has all T1 and judge-isolation lines passing; only the
  deliberately deferred CSV line fails.
