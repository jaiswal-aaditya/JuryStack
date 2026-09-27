from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentActor
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.errors import PermissionDenied
from app.core.models import (
    JudgeAssignment,
    JudgeTrackEligibility,
    Project,
    Team,
    TeamMember,
    Track,
    User,
)


class AuthorizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def require_owner(actor: User, owner_user_id: str) -> None:
        if actor.role not in {Role.ORGANIZER, Role.ADMIN} and actor.id != owner_user_id:
            raise PermissionDenied("This resource belongs to another user.")

    async def require_event_scope(self, actor: User, event_id: str) -> None:
        if actor.role in {Role.ORGANIZER, Role.ADMIN}:
            return
        if actor.role == Role.PARTICIPANT:
            allowed = await self.session.scalar(
                select(
                    exists().where(
                        TeamMember.user_id == actor.id,
                        TeamMember.team_id == Team.id,
                        Team.event_id == event_id,
                    )
                )
            )
        elif actor.role == Role.JUDGE:
            allowed = await self.session.scalar(
                select(
                    exists().where(
                        JudgeTrackEligibility.judge_id == actor.id,
                        JudgeTrackEligibility.track_id == Track.id,
                        Track.event_id == event_id,
                    )
                )
            )
        else:
            allowed = False
        if not allowed:
            raise PermissionDenied("Actor is outside this event's scope.")

    async def require_track_scope(self, actor: User, track_id: str) -> None:
        if actor.role in {Role.ORGANIZER, Role.ADMIN}:
            return
        if actor.role == Role.JUDGE:
            allowed = await self.session.scalar(
                select(
                    exists().where(
                        JudgeTrackEligibility.judge_id == actor.id,
                        JudgeTrackEligibility.track_id == track_id,
                    )
                )
            )
        elif actor.role == Role.PARTICIPANT:
            allowed = await self.session.scalar(
                select(
                    exists().where(
                        Track.id == track_id,
                        Team.event_id == Track.event_id,
                        TeamMember.team_id == Team.id,
                        TeamMember.user_id == actor.id,
                    )
                )
            )
        else:
            allowed = False
        if not allowed:
            raise PermissionDenied("Actor is outside this track's scope.")

    async def require_judge_assignment(
        self,
        actor: User,
        project_id: str,
        requested_judge_id: str | None = None,
        *,
        organizer_override: bool = False,
    ) -> None:
        if organizer_override and actor.role in {Role.ORGANIZER, Role.ADMIN}:
            return
        if actor.role != Role.JUDGE:
            raise PermissionDenied("A judge assignment is required.")
        if requested_judge_id and requested_judge_id != actor.id:
            raise PermissionDenied("Judges cannot access a peer's scorecard.")
        assigned = await self.session.scalar(
            select(
                exists().where(
                    JudgeAssignment.judge_id == actor.id,
                    JudgeAssignment.project_id == project_id,
                    JudgeAssignment.project_id == Project.id,
                    JudgeTrackEligibility.judge_id == actor.id,
                    JudgeTrackEligibility.track_id == Project.track_id,
                )
            )
        )
        if not assigned:
            raise PermissionDenied("The project is not assigned to this judge.")


def get_authorization_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthorizationService:
    return AuthorizationService(session)


def require_owned_resource(
    owner_parameter: str = "owner_user_id",
) -> Callable[..., User]:
    async def dependency(request: Request, actor: CurrentActor) -> User:
        owner_id = request.path_params.get(owner_parameter)
        if owner_id is None:
            owner_id = request.query_params.get(owner_parameter)
        if owner_id is None:
            raise PermissionDenied("Resource ownership could not be established.")
        AuthorizationService.require_owner(actor, owner_id)
        return actor

    return dependency


def require_event_access(event_parameter: str = "event_id") -> Callable[..., User]:
    async def dependency(
        request: Request,
        actor: CurrentActor,
        policy: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> User:
        event_id = request.path_params.get(event_parameter)
        if event_id is None:
            event_id = request.query_params.get(event_parameter)
        if event_id is None:
            raise PermissionDenied("Event scope could not be established.")
        await policy.require_event_scope(actor, event_id)
        return actor

    return dependency


def require_track_access(track_parameter: str = "track_id") -> Callable[..., User]:
    async def dependency(
        request: Request,
        actor: CurrentActor,
        policy: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> User:
        track_id = request.path_params.get(track_parameter)
        if track_id is None:
            track_id = request.query_params.get(track_parameter)
        if track_id is None:
            raise PermissionDenied("Track scope could not be established.")
        await policy.require_track_scope(actor, track_id)
        return actor

    return dependency


def require_assignment_access(
    project_parameter: str = "project_id",
    judge_parameter: str | None = "judge_id",
    *,
    organizer_override: bool = False,
) -> Callable[..., User]:
    async def dependency(
        request: Request,
        actor: CurrentActor,
        policy: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> User:
        project_id = request.path_params.get(project_parameter)
        if project_id is None:
            project_id = request.query_params.get(project_parameter)
        if project_id is None:
            raise PermissionDenied("Project scope could not be established.")
        judge_id = None
        if judge_parameter:
            judge_id = request.path_params.get(judge_parameter)
            if judge_id is None:
                judge_id = request.query_params.get(judge_parameter)
        await policy.require_judge_assignment(
            actor,
            project_id,
            judge_id,
            organizer_override=organizer_override,
        )
        return actor

    return dependency
