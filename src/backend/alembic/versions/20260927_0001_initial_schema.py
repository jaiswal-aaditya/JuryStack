"""Create the JuryStack relational schema.

Revision ID: 20260927_0001
Revises:
Create Date: 2026-09-27 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.String(512)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("submissions_close", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_slug", "events", ["slug"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "tracks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.UniqueConstraint("event_id", "name"),
    )
    op.create_table(
        "prizes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_index("ix_teams_event_name", "teams", ["event_id", "name"])
    op.create_table(
        "team_members",
        sa.Column(
            "team_id",
            sa.String(64),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_table(
        "team_invites",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "team_id",
            sa.String(64),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_team_invites_token_hash", "team_invites", ["token_hash"], unique=True
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.String(64),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "track_id", sa.String(64), sa.ForeignKey("tracks.id"), nullable=False
        ),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("repo_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_projects_event_track", "projects", ["event_id", "track_id"])
    op.create_index("ix_projects_team", "projects", ["team_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "custom_questions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("event_id", "position"),
    )
    op.create_table(
        "custom_answers",
        sa.Column(
            "project_id",
            sa.String(64),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "question_id",
            sa.String(64),
            sa.ForeignKey("custom_questions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("answer", sa.Text(), nullable=False),
    )

    op.create_table(
        "rubrics",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("event_id", "version"),
    )
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "rubric_id",
            sa.String(64),
            sa.ForeignKey("rubrics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("minimum_score", sa.Integer(), nullable=False),
        sa.Column("maximum_score", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("weight > 0", name="ck_rubric_criteria_weight_positive"),
        sa.CheckConstraint(
            "minimum_score < maximum_score", name="ck_rubric_score_range"
        ),
        sa.UniqueConstraint("rubric_id", "key"),
    )

    op.create_table(
        "judge_invitations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("accepted_by_user_id", sa.String(64), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_judge_invitations_email", "judge_invitations", ["email"])
    op.create_index(
        "ix_judge_invitations_token_hash",
        "judge_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_table(
        "judge_track_eligibility",
        sa.Column(
            "judge_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
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
        "ix_judge_track_eligibility_track_id",
        "judge_track_eligibility",
        ["track_id"],
    )
    op.create_table(
        "judge_assignments",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column(
            "judge_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(64),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("judge_id", "project_id"),
    )
    op.create_index(
        "ix_judge_assignments_project_id", "judge_assignments", ["project_id"]
    )
    op.create_table(
        "scorecards",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column(
            "judge_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(64),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rubric_id", sa.String(64), sa.ForeignKey("rubrics.id"), nullable=False
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("judge_id", "project_id", "rubric_id"),
    )
    op.create_index("ix_scorecards_judge_status", "scorecards", ["judge_id", "status"])
    op.create_table(
        "criterion_scores",
        sa.Column(
            "scorecard_id",
            sa.String(160),
            sa.ForeignKey("scorecards.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "criterion_id",
            sa.String(64),
            sa.ForeignKey("rubric_criteria.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "score >= 1 AND score <= 5", name="ck_criterion_score_range"
        ),
    )
    op.create_index(
        "ix_criterion_scores_criterion_id", "criterion_scores", ["criterion_id"]
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("event_id", sa.String(64), sa.ForeignKey("events.id")),
        sa.Column("actor_id", sa.String(64), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_events_event_id", "audit_events", ["event_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    for table_name in (
        "audit_events",
        "criterion_scores",
        "scorecards",
        "judge_assignments",
        "judge_track_eligibility",
        "judge_invitations",
        "rubric_criteria",
        "rubrics",
        "custom_answers",
        "custom_questions",
        "projects",
        "team_invites",
        "team_members",
        "teams",
        "prizes",
        "tracks",
        "sessions",
        "events",
        "users",
    ):
        op.drop_table(table_name)
