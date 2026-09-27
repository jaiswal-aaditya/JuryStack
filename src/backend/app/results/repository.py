from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import (
    Event,
    JudgeAssignment,
    Project,
    Rubric,
    Scorecard,
)


class ResultsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def event(self, event_id: str | None) -> Event | None:
        if event_id:
            return await self.session.get(Event, event_id)
        return await self.session.scalar(select(Event).order_by(Event.id).limit(1))

    async def projects(self, event_id: str) -> list[Project]:
        return list(
            (
                await self.session.scalars(
                    select(Project)
                    .where(Project.event_id == event_id)
                    .options(selectinload(Project.team), selectinload(Project.track))
                    .order_by(Project.id)
                )
            ).all()
        )

    async def assignments(self, event_id: str) -> list[JudgeAssignment]:
        return list(
            (
                await self.session.scalars(
                    select(JudgeAssignment)
                    .join(Project, Project.id == JudgeAssignment.project_id)
                    .where(Project.event_id == event_id)
                    .options(
                        selectinload(JudgeAssignment.judge),
                        selectinload(JudgeAssignment.project).selectinload(
                            Project.team
                        ),
                        selectinload(JudgeAssignment.project).selectinload(
                            Project.track
                        ),
                    )
                    .order_by(JudgeAssignment.project_id, JudgeAssignment.judge_id)
                )
            ).all()
        )

    async def scorecards(self, event_id: str) -> list[Scorecard]:
        return list(
            (
                await self.session.scalars(
                    select(Scorecard)
                    .join(Project, Project.id == Scorecard.project_id)
                    .where(Project.event_id == event_id)
                    .options(
                        selectinload(Scorecard.rubric).selectinload(Rubric.criteria),
                        selectinload(Scorecard.criterion_scores),
                    )
                    .order_by(Scorecard.project_id, Scorecard.judge_id)
                )
            )
            .unique()
            .all()
        )
