# Data model

The planned PostgreSQL schema uses stable string identifiers and explicit
tables for users, sessions, events, tracks, prizes, teams, team memberships and
invites, projects, custom questions and answers, rubrics and criteria, judge
invitations and eligibility, assignments, scorecards and criterion scores, and
append-only audit events.

All timestamps will be timezone-aware UTC values. Alembic is the production
migration mechanism. The fixture anomaly in which `tm_07` owns `prj_07` and
`prj_41` must be preserved, so projects will not have a unique constraint on
team ID.

This is a scaffold placeholder; column-level definitions and reviewed
constraints will be added with the first migration.
