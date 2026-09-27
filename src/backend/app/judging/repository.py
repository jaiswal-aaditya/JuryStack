from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import (
    CriterionScore,
    Event,
    JudgeAssignment,
    JudgeInvitation,
    JudgeInvitationTrack,
    JudgeTrackEligibility,
    Project,
    Rubric,
    Scorecard,
    Track,
    User,
)


class JudgingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def event(self, event_id: str) -> Event | None:
        return await self.session.scalar(
            select(Event)
            .options(selectinload(Event.tracks))
            .where(Event.id == event_id)
        )

    def rubric_query(self) -> Select[tuple[Rubric]]:
        return select(Rubric).options(selectinload(Rubric.criteria))

    async def rubrics(self, event_id: str) -> list[Rubric]:
        return list(
            (
                await self.session.scalars(
                    self.rubric_query()
                    .where(Rubric.event_id == event_id)
                    .order_by(Rubric.version.desc())
                )
            ).all()
        )

    async def next_rubric_version(self, event_id: str) -> int:
        value = await self.session.scalar(
            select(func.max(Rubric.version)).where(Rubric.event_id == event_id)
        )
        return (value or 0) + 1

    async def invitation_by_token(
        self, token_hash: str, *, lock: bool = False
    ) -> JudgeInvitation | None:
        query = (
            select(JudgeInvitation)
            .options(
                selectinload(JudgeInvitation.event),
                selectinload(JudgeInvitation.tracks).selectinload(
                    JudgeInvitationTrack.track
                ),
            )
            .where(JudgeInvitation.token_hash == token_hash)
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def invitations(self, event_id: str) -> list[JudgeInvitation]:
        return list(
            (
                await self.session.scalars(
                    select(JudgeInvitation)
                    .options(selectinload(JudgeInvitation.tracks))
                    .where(JudgeInvitation.event_id == event_id)
                    .order_by(JudgeInvitation.expires_at.desc())
                )
            ).all()
        )

    async def user_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def judges(self, event_id: str) -> list[User]:
        return list(
            (
                await self.session.scalars(
                    select(User)
                    .join(
                        JudgeTrackEligibility,
                        JudgeTrackEligibility.judge_id == User.id,
                    )
                    .join(Track, Track.id == JudgeTrackEligibility.track_id)
                    .where(User.role == "judge", Track.event_id == event_id)
                    .options(selectinload(User.track_eligibilities))
                    .order_by(User.display_name, User.id)
                )
            )
            .unique()
            .all()
        )

    def assignment_query(self) -> Select[tuple[JudgeAssignment]]:
        return select(JudgeAssignment).options(
            selectinload(JudgeAssignment.judge),
            selectinload(JudgeAssignment.project).selectinload(Project.track),
        )

    async def assignment(self, assignment_id: str) -> JudgeAssignment | None:
        return await self.session.scalar(
            self.assignment_query().where(JudgeAssignment.id == assignment_id)
        )

    async def assignment_pair(
        self, judge_id: str, project_id: str
    ) -> JudgeAssignment | None:
        return await self.session.scalar(
            self.assignment_query().where(
                JudgeAssignment.judge_id == judge_id,
                JudgeAssignment.project_id == project_id,
            )
        )

    async def assignments(self, event_id: str) -> list[JudgeAssignment]:
        return list(
            (
                await self.session.scalars(
                    self.assignment_query()
                    .join(Project, Project.id == JudgeAssignment.project_id)
                    .where(Project.event_id == event_id)
                    .order_by(JudgeAssignment.judge_id, JudgeAssignment.project_id)
                )
            ).all()
        )

    async def project(self, project_id: str) -> Project | None:
        return await self.session.scalar(
            select(Project)
            .options(selectinload(Project.track))
            .where(Project.id == project_id)
        )

    async def projects(self, event_id: str) -> list[Project]:
        return list(
            (
                await self.session.scalars(
                    select(Project)
                    .options(selectinload(Project.track))
                    .where(Project.event_id == event_id, Project.status == "submitted")
                    .order_by(Project.id)
                )
            ).all()
        )

    async def judge_projects(self, judge_id: str) -> list[Project]:
        return list(
            (
                await self.session.scalars(
                    select(Project)
                    .join(
                        JudgeAssignment,
                        JudgeAssignment.project_id == Project.id,
                    )
                    .join(
                        JudgeTrackEligibility,
                        (JudgeTrackEligibility.judge_id == judge_id)
                        & (JudgeTrackEligibility.track_id == Project.track_id),
                    )
                    .where(
                        JudgeAssignment.judge_id == judge_id,
                        Project.status == "submitted",
                    )
                    .options(selectinload(Project.track))
                    .order_by(Project.title, Project.id)
                )
            ).all()
        )

    async def eligible(self, judge_id: str, track_id: str) -> bool:
        return (
            await self.session.get(JudgeTrackEligibility, (judge_id, track_id))
            is not None
        )

    async def scorecard_exists(self, judge_id: str, project_id: str) -> bool:
        return (
            await self.session.scalar(
                select(Scorecard.id).where(
                    Scorecard.judge_id == judge_id,
                    Scorecard.project_id == project_id,
                )
            )
            is not None
        )

    async def assigned_project(self, judge_id: str, project_id: str) -> Project | None:
        return await self.session.scalar(
            select(Project)
            .join(JudgeAssignment, JudgeAssignment.project_id == Project.id)
            .join(
                JudgeTrackEligibility,
                (JudgeTrackEligibility.judge_id == judge_id)
                & (JudgeTrackEligibility.track_id == Project.track_id),
            )
            .where(
                Project.id == project_id,
                Project.status == "submitted",
                JudgeAssignment.judge_id == judge_id,
            )
            .options(selectinload(Project.track))
        )

    def scorecard_query(self) -> Select[tuple[Scorecard]]:
        return select(Scorecard).options(
            selectinload(Scorecard.judge),
            selectinload(Scorecard.project).selectinload(Project.track),
            selectinload(Scorecard.rubric).selectinload(Rubric.criteria),
            selectinload(Scorecard.criterion_scores).selectinload(
                CriterionScore.criterion
            ),
        )

    def private_scorecard_query(self, judge_id: str) -> Select[tuple[Scorecard]]:
        return (
            self.scorecard_query()
            .join(JudgeAssignment, JudgeAssignment.project_id == Scorecard.project_id)
            .join(Project, Project.id == Scorecard.project_id)
            .join(
                JudgeTrackEligibility,
                (JudgeTrackEligibility.judge_id == judge_id)
                & (JudgeTrackEligibility.track_id == Project.track_id),
            )
            .where(
                Scorecard.judge_id == judge_id,
                JudgeAssignment.judge_id == judge_id,
            )
        )

    async def judge_scorecards(self, judge_id: str) -> list[Scorecard]:
        return list(
            (
                await self.session.scalars(
                    self.private_scorecard_query(judge_id).order_by(
                        Scorecard.project_id, Scorecard.rubric_id
                    )
                )
            )
            .unique()
            .all()
        )

    async def judge_project_scorecards(
        self, judge_id: str, project_id: str
    ) -> list[Scorecard]:
        return list(
            (
                await self.session.scalars(
                    self.private_scorecard_query(judge_id).where(
                        Scorecard.project_id == project_id
                    )
                )
            )
            .unique()
            .all()
        )

    async def judge_scorecard(
        self, judge_id: str, scorecard_id: str, *, lock: bool = False
    ) -> Scorecard | None:
        query = self.private_scorecard_query(judge_id).where(
            Scorecard.id == scorecard_id
        )
        if lock:
            query = query.with_for_update(of=Scorecard)
        return await self.session.scalar(query)

    async def judge_project_rubric_scorecard(
        self, judge_id: str, project_id: str, rubric_id: str, *, lock: bool = False
    ) -> Scorecard | None:
        query = self.private_scorecard_query(judge_id).where(
            Scorecard.project_id == project_id,
            Scorecard.rubric_id == rubric_id,
        )
        if lock:
            query = query.with_for_update(of=Scorecard)
        return await self.session.scalar(query)

    async def rubric(self, rubric_id: str) -> Rubric | None:
        return await self.session.scalar(
            self.rubric_query().where(Rubric.id == rubric_id)
        )

    async def active_rubric(self, event_id: str) -> Rubric | None:
        return await self.session.scalar(
            self.rubric_query().where(
                Rubric.event_id == event_id, Rubric.is_active.is_(True)
            )
        )

    async def organizer_scorecards(self, event_id: str) -> list[Scorecard]:
        return list(
            (
                await self.session.scalars(
                    self.scorecard_query()
                    .join(Project, Project.id == Scorecard.project_id)
                    .where(Project.event_id == event_id)
                    .order_by(Scorecard.judge_id, Scorecard.project_id)
                )
            )
            .unique()
            .all()
        )
