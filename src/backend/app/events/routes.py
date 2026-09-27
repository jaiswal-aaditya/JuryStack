from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentActor, require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import User
from app.events.schemas import EventInput, EventResponse
from app.events.service import EventService

router = APIRouter(tags=["events"])
Organizer = Annotated[User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> EventService:
    return EventService(session)


@router.get("/api/events", response_model=list[EventResponse])
async def list_events(
    _: CurrentActor, service: Annotated[EventService, Depends(get_service)]
) -> list[EventResponse]:
    return [EventResponse.model_validate(item) for item in await service.list_events()]


@router.get("/api/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    _: CurrentActor,
    service: Annotated[EventService, Depends(get_service)],
) -> EventResponse:
    return EventResponse.model_validate(await service.get(event_id))


@router.post(
    "/api/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    payload: EventInput,
    actor: Organizer,
    service: Annotated[EventService, Depends(get_service)],
) -> EventResponse:
    return EventResponse.model_validate(await service.create(payload, actor))


@router.put("/api/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    payload: EventInput,
    actor: Organizer,
    service: Annotated[EventService, Depends(get_service)],
) -> EventResponse:
    return EventResponse.model_validate(await service.update(event_id, payload, actor))
