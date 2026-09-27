from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import Team, TeamInvite, TeamMember


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def query(self):
        return select(Team).options(
            selectinload(Team.memberships).selectinload(TeamMember.user)
        )

    async def for_user(self, user_id: str) -> list[Team]:
        query = (
            self.query()
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Team.name)
        )
        return list((await self.session.scalars(query)).unique().all())

    async def by_id(self, team_id: str) -> Team | None:
        return await self.session.scalar(self.query().where(Team.id == team_id))

    async def membership(self, team_id: str, user_id: str) -> TeamMember | None:
        return await self.session.get(TeamMember, (team_id, user_id))

    async def valid_invite(self, token_hash: str, now: datetime) -> TeamInvite | None:
        return await self.session.scalar(
            select(TeamInvite).where(
                TeamInvite.token_hash == token_hash, TeamInvite.expires_at > now
            )
        )

    async def expired_or_used_invite(self, token_hash: str) -> bool:
        return (
            await self.session.scalar(
                select(TeamInvite.id).where(TeamInvite.token_hash == token_hash)
            )
            is not None
        )

    async def consume_invite(self, invite_id: str) -> None:
        await self.session.execute(delete(TeamInvite).where(TeamInvite.id == invite_id))
