"""Add invitation expiry/scope and rubric descriptions.

Revision ID: 20260927_0004
Revises: 20260927_0003
Create Date: 2026-09-27 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0004"
down_revision: str | None = "20260927_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_criterion_score_range", "criterion_scores", type_="check"
    )
    op.create_check_constraint(
        "ck_criterion_score_range",
        "criterion_scores",
        "score >= 0 AND score <= 100",
    )
    op.add_column(
        "rubric_criteria",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "judge_invitations",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP + INTERVAL '24 hours'"),
        ),
    )
    op.create_index(
        "ix_judge_invitations_expires_at",
        "judge_invitations",
        ["expires_at"],
    )
    op.create_table(
        "judge_invitation_tracks",
        sa.Column(
            "invitation_id",
            sa.String(64),
            sa.ForeignKey("judge_invitations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "track_id",
            sa.String(64),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_judge_invitation_tracks_track_id",
        "judge_invitation_tracks",
        ["track_id"],
    )
    op.alter_column("rubric_criteria", "description", server_default=None)
    op.alter_column("judge_invitations", "expires_at", server_default=None)


def downgrade() -> None:
    op.drop_table("judge_invitation_tracks")
    op.drop_index("ix_judge_invitations_expires_at", table_name="judge_invitations")
    op.drop_column("judge_invitations", "expires_at")
    op.drop_column("rubric_criteria", "description")
    op.drop_constraint(
        "ck_criterion_score_range", "criterion_scores", type_="check"
    )
    op.create_check_constraint(
        "ck_criterion_score_range",
        "criterion_scores",
        "score >= 1 AND score <= 5",
    )
