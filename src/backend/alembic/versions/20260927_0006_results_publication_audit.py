"""Track results publication and enforce append-only audit rows.

Revision ID: 20260927_0006
Revises: 20260927_0005
Create Date: 2026-09-27 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0006"
down_revision: str | None = "20260927_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("results_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_audit_event_changes() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_changes()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION prevent_audit_event_changes()")
    op.drop_column("events", "results_published_at")
