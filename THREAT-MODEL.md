# Threat model

Security boundaries include opaque server-side sessions, role and ownership
checks, event and track scope, assignment isolation, server-authoritative UTC
deadlines, safe URL handling, CSV formula-injection prevention, and append-only
audit events. Secrets and session-token hashes must never be returned by APIs or
written to normal logs.

This placeholder will be expanded with assets, actors, abuse cases, controls,
and residual risks when the corresponding product features are implemented.
