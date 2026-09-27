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
scores. Scorecard editing and weighted-score calculation are intentionally not
part of this first Tier 2 slice.

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

## Deferred judging work

Private scorecard editing, progress monitoring, weighted raw-score output,
normalization, and results export remain separate later slices. Raw fixture
scores remain preserved. No normalization method is implemented or claimed;
its formula and fallbacks for constant scorers, one-review judges, incomplete
criteria, and insufficient overlap must be documented with deterministic tests
before Tier 2 is claimed.
