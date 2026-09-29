import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.security import hash_session_token
from app.core.errors import Conflict, InvalidRequest, ResourceNotFound
from app.core.models import Ballot, BallotEntry, Event, ProjectVote, User, VoterInvitation, VotingWindow
from app.voting.repository import VotingRepository
from app.voting.schemas import VoterInvitationCreate, VotingWindowUpsert


class VotingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = VotingRepository(session)

    async def _event(self, event_id: str) -> Event:
        event = await self.repository.event(event_id)
        if event is None:
            raise ResourceNotFound("Event not found.")
        return event

    async def upsert_voting_window(
        self, event_id: str, payload: VotingWindowUpsert, actor: User
    ) -> VotingWindow:
        await self._event(event_id)
        if payload.opens_at >= payload.closes_at:
            raise InvalidRequest(
                "voting_window_range",
                "The voting window must open before it closes.",
            )
        window = await self.repository.voting_window(event_id)
        creating = window is None
        if window is None:
            window = VotingWindow(
                id=f"vwin_{secrets.token_hex(10)}",
                event_id=event_id,
                opens_at=payload.opens_at,
                closes_at=payload.closes_at,
                is_enabled=payload.is_enabled,
            )
            self.session.add(window)
        else:
            window.opens_at = payload.opens_at
            window.closes_at = payload.closes_at
            window.is_enabled = payload.is_enabled
        record_audit(
            self.session,
            action="voting.window_upserted",
            actor_id=actor.id,
            event_id=event_id,
            detail={
                "created": creating,
                "opens_at": payload.opens_at.isoformat(),
                "closes_at": payload.closes_at.isoformat(),
                "is_enabled": payload.is_enabled,
            },
        )
        await self._commit("voting_window_conflict", "The voting window could not be saved.")
        refreshed = await self.repository.voting_window(event_id)
        assert refreshed is not None
        return refreshed

    async def create_voter_invitation(
        self, event_id: str, payload: VoterInvitationCreate, actor: User
    ) -> tuple[VoterInvitation, str]:
        await self._event(event_id)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        invitation = VoterInvitation(
            id=f"vin_{secrets.token_hex(12)}",
            event_id=event_id,
            email=payload.email.strip().casefold(),
            token_hash=hash_session_token(token),
            expires_at=expires_at,
        )
        self.session.add(invitation)
        record_audit(
            self.session,
            action="voting.invitation_issued",
            actor_id=actor.id,
            event_id=event_id,
            detail={"invitation_id": invitation.id, "email": invitation.email},
        )
        await self._commit(
            "voter_invitation_conflict", "The voter invitation could not be created."
        )
        return invitation, token

    async def redeem_ballot(self, token: str) -> Ballot:
        """Idempotently exchange a voter token for that voter's ballot.

        First call creates the ballot with a randomized project order and
        marks the invitation redeemed; later calls return the same ballot
        rather than erroring, so a page refresh never breaks the flow.
        """
        token_hash = hash_session_token(token)
        invitation = await self.repository.invitation_by_token_hash(
            token_hash, lock=True
        )
        if invitation is None:
            raise ResourceNotFound("Voting link not found.")
        if invitation.expires_at <= datetime.now(UTC):
            raise Conflict("invitation_expired", "This voting link has expired.")

        existing = await self.repository.ballot_by_invitation_id(invitation.id)
        if existing is not None:
            return existing

        window = await self.repository.voting_window(invitation.event_id)
        if not VotingRepository.is_open(window, now=datetime.now(UTC)):
            raise Conflict("voting_closed", "Voting is not currently open.")

        projects = await self.repository.submitted_projects(invitation.event_id)
        if not projects:
            raise Conflict("no_eligible_projects", "No projects are eligible for voting.")

        order = list(projects)
        secrets.SystemRandom().shuffle(order)

        ballot = Ballot(
            id=f"bal_{secrets.token_hex(14)}",
            event_id=invitation.event_id,
            voter_invitation_id=invitation.id,
        )
        ballot.entries = [
            BallotEntry(project_id=project.id, position=position)
            for position, project in enumerate(order)
        ]
        invitation.redeemed_at = datetime.now(UTC)
        self.session.add(ballot)
        record_audit(
            self.session,
            action="voting.ballot_created",
            actor_id=None,
            event_id=invitation.event_id,
            detail={"invitation_id": invitation.id, "ballot_id": ballot.id},
        )
        await self._commit("ballot_conflict", "The ballot could not be created.")
        created = await self.repository.ballot_by_invitation_id(invitation.id)
        assert created is not None
        return created

    async def cast_vote(self, token: str, project_id: str) -> ProjectVote:
        token_hash = hash_session_token(token)
        invitation = await self.repository.invitation_by_token_hash(token_hash)
        if invitation is None:
            raise ResourceNotFound("Voting link not found.")

        ballot = await self.repository.ballot_by_invitation_id(invitation.id)
        if ballot is None:
            raise Conflict(
                "ballot_not_created", "Load the ballot before submitting a vote."
            )

        window = await self.repository.voting_window(invitation.event_id)
        if not VotingRepository.is_open(window, now=datetime.now(UTC)):
            raise Conflict("voting_closed", "Voting is not currently open.")

        if ballot.vote is not None:
            raise Conflict("already_voted", "This ballot has already been cast.")

        eligible_project_ids = {entry.project_id for entry in ballot.entries}
        if project_id not in eligible_project_ids:
            raise InvalidRequest(
                "project_not_on_ballot", "That project is not on this ballot."
            )

        vote = ProjectVote(
            id=f"vote_{secrets.token_hex(14)}",
            ballot_id=ballot.id,
            project_id=project_id,
        )
        self.session.add(vote)
        record_audit(
            self.session,
            action="voting.vote_cast",
            actor_id=None,
            event_id=invitation.event_id,
            detail={"ballot_id": ballot.id, "project_id": project_id},
        )
        await self._commit("already_voted", "This ballot has already been cast.")
        return vote

    async def _commit(self, code: str, message: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise Conflict(code, message) from error