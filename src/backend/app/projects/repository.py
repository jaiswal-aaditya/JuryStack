from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import CustomAnswer, Project, Team, TeamMember


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def query(self):
        return select(Project).options(
            selectinload(Project.event),
            selectinload(Project.team),
            selectinload(Project.track),
            selectinload(Project.custom_answers),
        )

    async def by_id(self, project_id: str) -> Project | None:
        return await self.session.scalar(self.query().where(Project.id == project_id))

    async def mine(self, user_id: str) -> list[Project]:
        query = (
            self.query()
            .join(Team, Team.id == Project.team_id)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Project.title)
        )
        return list((await self.session.scalars(query)).unique().all())

    async def is_member(self, team_id: str, user_id: str) -> bool:
        return await self.session.get(TeamMember, (team_id, user_id)) is not None

    async def first_team(self, user_id: str) -> Team | None:
        return await self.session.scalar(
            select(Team)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Team.id)
        )

    async def gallery(
        self, search: str | None, track_id: str | None, limit: int, offset: int
    ) -> tuple[list[Project], int]:
        conditions = [Project.status == "submitted"]
        if track_id:
            conditions.append(Project.track_id == track_id)
        if search:
            pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Project.title.ilike(pattern),
                    Project.summary.ilike(pattern),
                    Team.name.ilike(pattern),
                )
            )
        base = select(Project).join(Team, Team.id == Project.team_id).where(*conditions)
        total = int(
            await self.session.scalar(select(func.count()).select_from(base.subquery()))
            or 0
        )
        query = (
            self.query()
            .join(Team, Team.id == Project.team_id)
            .where(*conditions)
            .order_by(Project.submitted_at.desc(), Project.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.scalars(query)).unique().all()), total

    async def replace_answers(self, project: Project, answers: dict[str, str]) -> None:
        existing = {answer.question_id: answer for answer in project.custom_answers}
        project.custom_answers[:] = [
            existing.get(question_id)
            or CustomAnswer(project_id=project.id, question_id=question_id)
            for question_id in answers
        ]
        for answer in project.custom_answers:
            answer.answer = answers[answer.question_id]
