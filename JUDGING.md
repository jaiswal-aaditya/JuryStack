# Judging

The T2 design will support organizer-defined weighted rubrics, track-scoped
assignments, private per-judge scorecards, progress monitoring, normalization,
and CSV export. Raw scores will remain immutable inputs to derived normalized
results. Authorization will be enforced by FastAPI, including denial of peer
score access and participant access to judge APIs.

The normalization formula and fallbacks for constant scorers, one-review
judges, incomplete criteria, and insufficient overlap are deliberately not
specified during the scaffold phase. They must be documented here together
with deterministic tests before T2 is marked complete.
