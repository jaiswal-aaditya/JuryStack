from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import Ballot, User, VoterInvitation, VotingWindow
from app.voting.schemas import (
    BallotEntryResponse,
    BallotResponse,
    VoteCreate,
    VoteResponse,
    VoterInvitationCreate,
    VoterInvitationResponse,
    VotingWindowResponse,
    VotingWindowUpsert,
)
from app.voting.service import VotingService

router = APIRouter(prefix="/api", tags=["voting"])
Organizer = Annotated[User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VotingService:
    return VotingService(session)


def voting_window_response(window: VotingWindow) -> VotingWindowResponse:
    return VotingWindowResponse(
        id=window.id,
        event_id=window.event_id,
        opens_at=window.opens_at,
        closes_at=window.closes_at,
        is_enabled=window.is_enabled,
    )


def voter_invitation_response(
    invitation: VoterInvitation, invitation_url: str | None = None
) -> VoterInvitationResponse:
    return VoterInvitationResponse(
        id=invitation.id,
        event_id=invitation.event_id,
        email=invitation.email,
        expires_at=invitation.expires_at,
        invitation_url=invitation_url,
    )


def ballot_response(ballot: Ballot) -> BallotResponse:
    return BallotResponse(
        id=ballot.id,
        event_id=ballot.event_id,
        entries=[
            BallotEntryResponse(
                project_id=entry.project_id,
                title=entry.project.title,
                summary=entry.project.summary,
                track_name=entry.project.track.name,
                position=entry.position,
            )
            for entry in sorted(ballot.entries, key=lambda item: item.position)
        ],
        has_voted=ballot.vote is not None,
    )


@router.put(
    "/events/{event_id}/voting-window",
    response_model=VotingWindowResponse,
)
async def upsert_voting_window(
    event_id: str,
    payload: VotingWindowUpsert,
    actor: Organizer,
    service: Annotated[VotingService, Depends(get_service)],
) -> VotingWindowResponse:
    return voting_window_response(
        await service.upsert_voting_window(event_id, payload, actor)
    )


@router.post(
    "/events/{event_id}/voter-invitations",
    response_model=VoterInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voter_invitation(
    event_id: str,
    payload: VoterInvitationCreate,
    actor: Organizer,
    service: Annotated[VotingService, Depends(get_service)],
) -> VoterInvitationResponse:
    invitation, token = await service.create_voter_invitation(event_id, payload, actor)
    return voter_invitation_response(invitation, f"/vote/{token}")


@router.get("/voting/{token}/ballot", response_model=BallotResponse)
async def get_ballot(
    token: str,
    service: Annotated[VotingService, Depends(get_service)],
) -> BallotResponse:
    return ballot_response(await service.redeem_ballot(token))


@router.post("/voting/{token}/vote", response_model=VoteResponse)
async def cast_vote(
    token: str,
    payload: VoteCreate,
    service: Annotated[VotingService, Depends(get_service)],
) -> VoteResponse:
    vote = await service.cast_vote(token, payload.project_id)
    return VoteResponse(id=vote.id, project_id=vote.project_id, cast_at=vote.cast_at)