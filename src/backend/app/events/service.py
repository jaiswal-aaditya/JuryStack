import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.errors import Conflict, ResourceNotFound
from app.core.models import CustomQuestion, Event, Prize, Track, User
from app.events.repository import EventRepository
from app.events.schemas import EventInput


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = EventRepository(session)

    async def list_events(self) -> list[Event]:
        return await self.repository.all()

    async def get(self, event_id: str) -> Event:
        event = await self.repository.by_id(event_id)
        if event is None:
            raise ResourceNotFound("Event not found.")
        return event

    async def create(self, payload: EventInput, actor: User) -> Event:
        if await self.repository.slug_exists(payload.slug):
            raise Conflict("slug_in_use", "An event already uses this slug.")
        event = Event(
            id=f"evt_{secrets.token_hex(10)}",
            slug=payload.slug,
            name=payload.name.strip(),
            starts_at=payload.starts_at,
            submissions_open=payload.submissions_open,
            submissions_close=payload.submissions_close,
        )
        self.session.add(event)
        self._replace_configuration(event, payload)
        record_audit(
            self.session,
            action="event.created",
            actor_id=actor.id,
            event_id=event.id,
            detail={"name": event.name, "slug": event.slug},
        )
        await self._commit()
        return await self.get(event.id)

    async def update(self, event_id: str, payload: EventInput, actor: User) -> Event:
        event = await self.get(event_id)
        if await self.repository.slug_exists(payload.slug, except_id=event_id):
            raise Conflict("slug_in_use", "An event already uses this slug.")
        event.slug = payload.slug
        event.name = payload.name.strip()
        event.starts_at = payload.starts_at
        event.submissions_open = payload.submissions_open
        event.submissions_close = payload.submissions_close
        self._replace_configuration(event, payload)
        record_audit(
            self.session,
            action="event.updated",
            actor_id=actor.id,
            event_id=event.id,
            detail={"name": event.name, "slug": event.slug},
        )
        await self._commit()
        return await self.get(event.id)

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise Conflict(
                "event_configuration_conflict",
                "The event configuration conflicts with existing data.",
            ) from error

    def _replace_configuration(self, event: Event, payload: EventInput) -> None:
        track_by_id = {item.id: item for item in event.tracks}
        prize_by_id = {item.id: item for item in event.prizes}
        question_by_id = {item.id: item for item in event.custom_questions}

        event.tracks[:] = [
            track_by_id.get(item.id)
            or Track(id=item.id or f"trk_{secrets.token_hex(10)}")
            for item in payload.tracks
        ]
        for model, item in zip(event.tracks, payload.tracks, strict=True):
            model.name = item.name.strip()

        event.prizes[:] = [
            prize_by_id.get(item.id)
            or Prize(id=item.id or f"prz_{secrets.token_hex(10)}")
            for item in payload.prizes
        ]
        for model, item in zip(event.prizes, payload.prizes, strict=True):
            model.name = item.name.strip()
            model.description = item.description.strip()

        event.custom_questions[:] = [
            question_by_id.get(item.id)
            or CustomQuestion(id=item.id or f"qst_{secrets.token_hex(10)}")
            for item in payload.custom_questions
        ]
        for position, (model, item) in enumerate(
            zip(event.custom_questions, payload.custom_questions, strict=True), start=1
        ):
            model.prompt = item.prompt.strip()
            model.required = item.required
            model.position = position
