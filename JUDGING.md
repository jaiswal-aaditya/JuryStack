# Judging

## Rubrics

An organizer defines one or more ordered criteria with a label, description,
minimum and maximum integer score, and positive integer weight. Weights are
relative rather than percentages, so they do not have to sum to 100. The API
rejects blank or duplicate labels, duplicate display positions, non-positive
weights, and ranges where `minimum_score >= maximum_score`.

Every save creates the next event rubric version and marks the previous version
inactive. It never edits historical criteria. A scorecard references its exact
rubric version, so a later organizer change cannot silently reinterpret stored
scores. Private scorecard editing is implemented below. Organizer result rows
calculate a raw weighted average as
`sum(score × criterion weight) / sum(scored weights)`; an incomplete draft
reports only criteria actually present and is never treated as a submitted
review.

## Judge invitations and assignment

Invitations are fully local: the organizer selects an email, event tracks, and
expiry, then receives a link to copy directly. Tokens are generated from 32
random bytes, returned only at creation, stored only as SHA-256 hashes, and
consumed once under a row lock. Expired and previously accepted links are
rejected. Accepting a link creates a local password-backed judge account or
requires the already registered invited account to be signed in, then grants
only the invitation's track eligibility.

Organizers can create and remove individual assignments and inspect every
assignment in an event. Only submitted projects may be assigned, duplicate
judge/project pairs are rejected in both the service and database, and a judge
must be eligible for the project's track. Assignments backed by an existing
scorecard cannot be removed.

Balanced batches top each selected project up to the requested review count.
The deterministic planner accounts for existing assignments, chooses the
least-loaded eligible judge (stable judge ID breaks ties), never duplicates a
pair, and rejects the whole batch before writing if any project has too few
eligible judges. A judge's project list joins both their own assignments and
current track eligibility. Participants and other roles cannot use judge or
assignment-management routes.

Rubric changes, invitation creation/acceptance, and assignment changes append
human-readable action names with structured JSON detail to `audit_events` in
the same transaction.

## Private scorecards and isolation

A judge can list only scorecards joined to their authenticated user ID, an
existing assignment, and current eligibility for the project's track. The
checker-compatible `judge_id` query is accepted only when it equals the actor;
requesting another judge returns `403` before score data is queried. Detail
lookups also include the actor and assignment scope, so a guessed peer
scorecard ID returns an undisclosed `404`. Participants receive `403` at the
role boundary. Judge responses, frontend queries, errors, and submission audit
details contain no peer comments or criterion values.

Drafts are keyed by judge, project, and rubric version. A draft can contain a
subset of criteria and can be saved repeatedly to the same logical row. Every
criterion ID must belong to that rubric and every integer value must fall in
its configured inclusive range. Submission is a separate action requiring all
criteria; it sets the server UTC timestamp, records
`judge.scorecard_submitted` without score/comment content, and makes the card
read-only. A new active rubric never rewrites a prior submitted card.
After any in-progress draft is completed, the judge workspace selects the
active rubric and starts a distinct logical card when only historical submitted
versions exist.

Organizers inspect raw scorecards and latest-per-assignment progress through
separate organizer-role endpoints. These endpoints are not exposed to judges.

## Organizer operations and remaining work

The organizer operations page reports missing, draft, and submitted assignment
counts, completion percentage, and projects below a configurable submitted
review target. It supports track, judge, project, and completion-state filters.
The CSV export includes stable migration IDs, relationship labels, statuses,
review counts, rubric identity, and raw weighted scores; every cell beginning
with a spreadsheet formula character is prefixed with an apostrophe.

Raw fixture scores remain preserved. Cross-judge normalization is still not
implemented or claimed; its formula and fallbacks for constant scorers,
one-review judges, incomplete criteria, and insufficient overlap must be
documented with deterministic tests before Tier 2 is claimed.
