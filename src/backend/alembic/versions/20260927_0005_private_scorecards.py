"""Constrain private scorecard lifecycle state.

Revision ID: 20260927_0005
Revises: 20260927_0004
Create Date: 2026-09-27 15:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260927_0005"
down_revision: str | None = "20260927_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_scorecards_status",
        "scorecards",
        "status IN ('draft', 'submitted')",
    )
    op.create_check_constraint(
        "ck_scorecards_submission_state",
        "scorecards",
        "(status = 'draft' AND submitted_at IS NULL) OR "
        "(status = 'submitted' AND submitted_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_scorecards_submission_state", "scorecards", type_="check"
    )
    op.drop_constraint("ck_scorecards_status", "scorecards", type_="check")
