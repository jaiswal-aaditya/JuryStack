from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def query(self):
        return select(Event).options(
            selectinload(Event.tracks),
            selectinload(Event.prizes),
            selectinload(Event.custom_questions),
        )

    async def all(self) -> list[Event]:
        return list(
            (await self.session.scalars(self.query().order_by(Event.name))).all()
        )

    async def by_id(self, event_id: str) -> Event | None:
        return await self.session.scalar(self.query().where(Event.id == event_id))

    async def slug_exists(self, slug: str, except_id: str | None = None) -> bool:
        query = select(Event.id).where(Event.slug == slug)
        if except_id:
            query = query.where(Event.id != except_id)
        return await self.session.scalar(query) is not None
