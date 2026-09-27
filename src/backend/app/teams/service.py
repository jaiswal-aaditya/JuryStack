import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.errors import Conflict, PermissionDenied, ResourceNotFound
from app.core.models import Event, Team, TeamInvite, TeamMember, User
from app.teams.repository import TeamRepository


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = TeamRepository(session)

    async def list_for_actor(self, actor: User) -> list[Team]:
        return await self.repository.for_user(actor.id)

    async def create(self, event_id: str, name: str, actor: User) -> Team:
        if await self.session.get(Event, event_id) is None:
            raise ResourceNotFound("Event not found.")
        team = Team(
            id=f"tm_{secrets.token_hex(10)}", event_id=event_id, name=name.strip()
        )
        team.memberships.append(TeamMember(user_id=actor.id))
        self.session.add(team)
        record_audit(
            self.session,
            action="team.created",
            actor_id=actor.id,
            event_id=event_id,
            detail={"team_id": team.id, "name": team.name},
        )
        await self.session.commit()
        found = await self.repository.by_id(team.id)
        assert found is not None
        return found

    async def create_invite(
        self, team_id: str, expires_in_hours: int, actor: User
    ) -> tuple[str, datetime]:
        team = await self.repository.by_id(team_id)
        if team is None:
            raise ResourceNotFound("Team not found.")
        if await self.repository.membership(team_id, actor.id) is None:
            raise PermissionDenied("Only team members can invite teammates.")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)
        self.session.add(
            TeamInvite(
                id=f"tiv_{secrets.token_hex(10)}",
                team_id=team_id,
                token_hash=hash_invite_token(token),
                expires_at=expires_at,
            )
        )
        record_audit(
            self.session,
            action="team.invite_created",
            actor_id=actor.id,
            event_id=team.event_id,
            detail={"team_id": team_id, "expires_at": expires_at.isoformat()},
        )
        await self.session.commit()
        return token, expires_at

    async def accept_invite(self, token: str, actor: User) -> Team:
        token_hash = hash_invite_token(token)
        invite = await self.repository.valid_invite(token_hash, datetime.now(UTC))
        if invite is None:
            if await self.repository.expired_or_used_invite(token_hash):
                raise Conflict("invite_expired", "This invite has expired.")
            raise ResourceNotFound("Invite not found or already used.")
        team = await self.repository.by_id(invite.team_id)
        assert team is not None
        if await self.repository.membership(team.id, actor.id):
            raise Conflict("already_a_member", "You already belong to this team.")
        self.session.add(TeamMember(team_id=team.id, user_id=actor.id))
        await self.repository.consume_invite(invite.id)
        record_audit(
            self.session,
            action="team.invite_accepted",
            actor_id=actor.id,
            event_id=team.event_id,
            detail={"team_id": team.id},
        )
        await self.session.commit()
        found = await self.repository.by_id(team.id)
        assert found is not None
        return found
