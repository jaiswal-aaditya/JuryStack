from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentActor, require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import Team, User
from app.teams.schemas import (
    InviteCreate,
    InviteResponse,
    MemberResponse,
    TeamCreate,
    TeamResponse,
)
from app.teams.service import TeamService

router = APIRouter(prefix="/api", tags=["teams"])
Participant = Annotated[User, Depends(require_roles(Role.PARTICIPANT))]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TeamService:
    return TeamService(session)


def response(team: Team) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        event_id=team.event_id,
        name=team.name,
        members=[MemberResponse.model_validate(item.user) for item in team.memberships],
    )


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    actor: CurrentActor, service: Annotated[TeamService, Depends(get_service)]
) -> list[TeamResponse]:
    return [response(team) for team in await service.list_for_actor(actor)]


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    actor: Participant,
    service: Annotated[TeamService, Depends(get_service)],
) -> TeamResponse:
    return response(await service.create(payload.event_id, payload.name, actor))


@router.post("/teams/{team_id}/invites", response_model=InviteResponse)
async def create_invite(
    team_id: str,
    payload: InviteCreate,
    actor: Participant,
    service: Annotated[TeamService, Depends(get_service)],
) -> InviteResponse:
    token, expires_at = await service.create_invite(
        team_id, payload.expires_in_hours, actor
    )
    return InviteResponse(token=token, expires_at=expires_at)


@router.post("/team-invites/{token}/accept", response_model=TeamResponse)
async def accept_invite(
    token: str,
    actor: Participant,
    service: Annotated[TeamService, Depends(get_service)],
) -> TeamResponse:
    return response(await service.accept_invite(token, actor))
