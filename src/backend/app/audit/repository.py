from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_events(
        self,
        *,
        event_id: str | None,
        actor_id: str | None,
        action: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        limit: int,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).options(selectinload(AuditEvent.actor))
        if event_id:
            query = query.where(AuditEvent.event_id == event_id)
        if actor_id:
            query = query.where(AuditEvent.actor_id == actor_id)
        if action:
            query = query.where(AuditEvent.action.startswith(action))
        if occurred_from:
            query = query.where(AuditEvent.occurred_at >= occurred_from)
        if occurred_to:
            query = query.where(AuditEvent.occurred_at <= occurred_to)
        return list(
            (
                await self.session.scalars(
                    query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id).limit(
                        limit
                    )
                )
            ).all()
        )
