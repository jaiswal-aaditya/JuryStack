# Data model

Alembic revisions through `20260927_0003` create the normalized PostgreSQL
schema and add optional event start and submission-open timestamps. SQLAlchemy
2 typed models declare bidirectional relationships; services use those
relationships, while migrations remain the only production schema-management
mechanism. `Base.metadata.create_all()` is not used.

## Relations and integrity

| Area | Tables | Important integrity rules |
|---|---|---|
| Identity | `users`, `sessions` | Stable string IDs; unique normalized email and session-token hash; indexed roles and expirations; sessions reference users. |
| Event setup | `events`, `tracks`, `prizes`, `custom_questions` | Unique event slug, track name per event, and question position per event; aware UTC `starts_at`, `submissions_open`, and required `submissions_close`; all children reference an event. |
| Teams | `teams`, `team_members`, `team_invites` | `team_members` is an explicit many-to-many association with a composite primary key; only unique token hashes are stored; expiry is UTC and successful acceptance deletes the single-purpose invite. |
| Submissions | `projects`, `custom_answers` | Projects reference event, team, and track; drafts have no `submitted_at`, while submission atomically sets `submitted` and the server timestamp; answers use a project/question composite key. There is intentionally no unique constraint on `projects.team_id`. |
| Judging | `rubrics`, `rubric_criteria`, `judge_invitations`, `judge_track_eligibility`, `judge_assignments`, `scorecards`, `criterion_scores` | Versioned rubrics, positive criterion weights and bounded score ranges; eligibility is an explicit judge/track association; assignments are unique per judge/project; scorecards are unique per judge/project/rubric; criterion scores use a composite key. |
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
