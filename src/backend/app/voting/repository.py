from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import (
    Ballot,
    BallotEntry,
    Event,
    Project,
    ProjectVote,
    VoterInvitation,
    VotingWindow,
)


class VotingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def event(self, event_id: str) -> Event | None:
        return await self.session.get(Event, event_id)

    async def voting_window(self, event_id: str) -> VotingWindow | None:
        return await self.session.scalar(
            select(VotingWindow).where(VotingWindow.event_id == event_id)
        )

    async def submitted_projects(self, event_id: str) -> list[Project]:
        return list(
            (
                await self.session.scalars(
                    select(Project).where(
                        Project.event_id == event_id,
                        Project.status == "submitted",
                    )
                )
            ).all()
        )

    async def project(self, project_id: str) -> Project | None:
        return await self.session.get(Project, project_id)

    async def invitation_by_token_hash(
        self, token_hash: str, *, lock: bool = False
    ) -> VoterInvitation | None:
        query = select(VoterInvitation).where(
            VoterInvitation.token_hash == token_hash
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def ballot_by_invitation_id(self, invitation_id: str) -> Ballot | None:
        return await self.session.scalar(
            select(Ballot)
            .where(Ballot.voter_invitation_id == invitation_id)
            .options(
                selectinload(Ballot.entries)
                .selectinload(BallotEntry.project)
                .selectinload(Project.track),
                selectinload(Ballot.vote),
            )
        )

    async def ballot(self, ballot_id: str, *, lock: bool = False) -> Ballot | None:
        query = (
            select(Ballot)
            .where(Ballot.id == ballot_id)
            .options(
                selectinload(Ballot.entries)
                .selectinload(BallotEntry.project)
                .selectinload(Project.track),
                selectinload(Ballot.vote),
                selectinload(Ballot.voter_invitation),
            )
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def entries_for_ballot(self, ballot_id: str) -> list[BallotEntry]:
        return list(
            (
                await self.session.scalars(
                    select(BallotEntry)
                    .where(BallotEntry.ballot_id == ballot_id)
                    .order_by(BallotEntry.position)
                )
            ).all()
        )

    async def vote_for_ballot(self, ballot_id: str) -> ProjectVote | None:
        return await self.session.scalar(
            select(ProjectVote).where(ProjectVote.ballot_id == ballot_id)
        )

    @staticmethod
    def is_open(window: VotingWindow | None, *, now: datetime) -> bool:
        if window is None or not window.is_enabled:
            return False
        return window.opens_at <= now <= window.closes_at