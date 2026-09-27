"""Constrain authenticated actor roles.

Revision ID: 20260927_0002
Revises: 20260927_0001
Create Date: 2026-09-27 00:02:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

DEMO_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$TOqQQT8n45N+FhxOXUh5Sg$"
    "/zhEgVBSnMNGyFJuhEj6/0prrYP/KdnGdF+0+ogKaG8"
)

revision: str = "20260927_0002"
down_revision: str | None = "20260927_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('participant', 'judge', 'organizer', 'admin')",
    )
    op.execute(
        sa.text(
            "UPDATE users SET password_hash = :password_hash "
            "WHERE password_hash IS NULL"
        )
        .bindparams(password_hash=DEMO_PASSWORD_HASH)
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
