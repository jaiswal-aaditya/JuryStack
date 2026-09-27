import json
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditEvent


def record_audit(
    session: AsyncSession,
    *,
    action: str,
    actor_id: str | None,
    event_id: str | None,
    detail: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            id=f"audit_{secrets.token_hex(16)}",
            event_id=event_id,
            actor_id=actor_id,
            action=action,
            detail=json.dumps(detail, sort_keys=True),
        )
    )
