# Data model

Alembic revisions through `20260927_0005` create the normalized PostgreSQL
schema, add optional event start and submission-open timestamps, and complete
the first judging slice's invitation and rubric fields. SQLAlchemy 2 typed
models declare bidirectional relationships; services use those relationships,
while migrations remain the only production schema-management mechanism.
`Base.metadata.create_all()` is not used.

## Relations and integrity

| Area | Tables | Important integrity rules |
|---|---|---|
| Identity | `users`, `sessions` | Stable string IDs; unique normalized email and session-token hash; indexed roles and expirations; sessions reference users. |
| Event setup | `events`, `tracks`, `prizes`, `custom_questions` | Unique event slug, track name per event, and question position per event; aware UTC `starts_at`, `submissions_open`, and required `submissions_close`; all children reference an event. |
| Teams | `teams`, `team_members`, `team_invites` | `team_members` is an explicit many-to-many association with a composite primary key; only unique token hashes are stored; expiry is UTC and successful acceptance deletes the single-purpose invite. |
| Submissions | `projects`, `custom_answers` | Projects reference event, team, and track; drafts have no `submitted_at`, while submission atomically sets `submitted` and the server timestamp; answers use a project/question composite key. There is intentionally no unique constraint on `projects.team_id`. |
| Judging | `rubrics`, `rubric_criteria`, `judge_invitations`, `judge_invitation_tracks`, `judge_track_eligibility`, `judge_assignments`, `scorecards`, `criterion_scores` | Versioned rubrics preserve criterion label, description, relative positive weight, configured range, and display order. Invitation token hashes are unique, expiring, single-use records with event-track scope. Eligibility is an explicit judge/track association; assignments are unique per judge/project; scorecards are unique per judge/project/rubric. The broad 0–100 database constraint is narrowed to each criterion's configured range by the scorecard service before writes. |
| Audit | `audit_events` | Stable IDs and indexed event, action, and occurrence time; application services will enforce append-only writes. |

Foreign keys, uniqueness constraints, checks, and lookup indexes are defined in
both SQLAlchemy metadata and the reviewed migration. Timestamp columns use
PostgreSQL `timestamptz`; fixture parsing rejects malformed shapes and retains
aware UTC values at the API/import boundary.

## Tier 1 lifecycle invariants

Organizer event writes replace the ordered event configuration in one
transaction. Team creation adds the creator as the first member. Invite tokens
are returned only when created, stored only as SHA-256 hashes, expire after a
bounded interval, and are deleted after one successful use. Project ownership
is derived from `team_members`; direct requests by other participants receive
`403`. Only submitted projects appear in public queries, and required custom
questions are enforced when moving a draft to `submitted`.

## Official fixture import

The loader validates `fixtures.json` without rewriting it, constructs rows in
dependency order, and inserts the entire set in one transaction. PostgreSQL
`ON CONFLICT DO NOTHING` targets stable primary/logical keys, so a repeated
startup neither multiplies nor rewrites existing fixture records. A failure
rolls back the whole import.

The imported official data contains 8 tracks, 30 judges, 40 teams, 41 projects,
126 scorecards, and 378 criterion-score rows. `tm_07` retains both `prj_07` and
`prj_41`. Empty comments, exact score values, review counts from two through
five, and constant scorer `jdg_07` are preserved. The three raw fixture criteria
map to a seeded versioned rubric without normalization or repair.

Fixture judges become local judge users with their track eligibility. Fixture
team-member emails become deterministic participant users. The four local-only
checker sessions map as follows; only SHA-256 token hashes are stored:

| Checker actor | Database actor | Cookie token |
|---|---|---|
| organizer | `usr_organizer` | `org_7f2a` |
| judge_a | `jdg_01` | `jdg_a_91bc` |
| judge_b | `jdg_02` | `jdg_b_44de` |
| participant | deterministic user for the first fixture team member | `prt_2e88` |

## First Tier 2 judging slice

Saving a rubric creates a new `(event_id, version)` row and deactivates the
previous active version instead of editing it. Existing scorecards retain their
foreign key to the exact historical rubric. Judge invitations store only a
SHA-256 token hash, an expiry, accepted-user marker, and explicit event tracks;
acceptance locks the row before consuming it and adds the resulting judge-track
eligibility. Manual and balanced assignments share the database uniqueness
rule on `(judge_id, project_id)`. Assignment services admit only submitted
projects and eligible judge/project track pairs.

## Private scorecard lifecycle

`scorecards` has one row per `(judge_id, project_id, rubric_id)`. Database
checks allow only `draft` with a null submission time or `submitted` with a
non-null submission time. `criterion_scores` remains a composite child keyed by
scorecard and criterion; draft replacement is transactional and delete-orphan
managed. The application validates criterion membership and the rubric's exact
inclusive bounds before writing. Submitted cards are immutable through judge
services, and historical cards continue to reference their original rubric.
