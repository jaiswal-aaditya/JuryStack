# Threat model

Security boundaries include opaque server-side sessions, role and ownership
checks, event and track scope, assignment isolation, server-authoritative UTC
deadlines, safe URL handling, CSV formula-injection prevention, and append-only
audit events. Secrets and session-token hashes must never be returned by APIs or
written to normal logs.

Tier 1 protects the following assets and boundaries:

- Opaque session tokens are HttpOnly, only hashes persist, login rotates the
  presented session, and logout deletes it server-side.
- Event configuration is organizer-only. Participant project writes require a
  current team-membership row; knowing another project's ID is insufficient.
- Team invite tokens are random, hash-only, time-bounded, single-purpose, and
  removed on acceptance. Nonmembers cannot mint an invite for another team.
- The API validates event/track relationships, restricts URLs to HTTP(S),
  checks required custom answers, and uses a consistent safe error envelope.
- Deadline decisions use server UTC at each write boundary. Browser deadline
  messaging is informational and cannot authorize a late direct request.
- Public queries expose submitted projects only. Drafts remain behind the
  authenticated ownership check.
- Event, team, invite, project, and submission transitions append human-readable
  audit events without raw tokens or passwords.

Residual Tier 1 risks include local demo credentials (documented as local-only),
no per-IP rate limiting, and no CSRF token beyond SameSite=Lax cookies. Deployment
outside the local hackathon runtime must enable secure cookies, replace all demo
credentials, terminate TLS, and add appropriate edge abuse controls.
