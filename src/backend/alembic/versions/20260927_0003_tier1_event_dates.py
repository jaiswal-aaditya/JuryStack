"""Add configurable Tier 1 event dates.

Revision ID: 20260927_0003
Revises: 20260927_0002
Create Date: 2026-09-27 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0003"
down_revision: str | None = "20260927_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("starts_at", sa.DateTime(timezone=True)))
    op.add_column(
        "events", sa.Column("submissions_open", sa.DateTime(timezone=True))
    )
    op.create_check_constraint(
        "ck_events_submission_window",
        "events",
        "submissions_open IS NULL OR submissions_open < submissions_close",
    )
    op.create_check_constraint(
        "ck_projects_status",
        "projects",
        "status IN ('draft', 'submitted')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_projects_status", "projects", type_="check")
    op.drop_constraint("ck_events_submission_window", "events", type_="check")
    op.drop_column("events", "submissions_open")
    op.drop_column("events", "starts_at")
