import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.errors import ResourceNotFound
from app.core.models import JudgeAssignment, Project, Scorecard, User
from app.results.repository import ResultsRepository
from app.results.schemas import (
    AssignmentProgress,
    OrganizerProgressResponse,
    ProgressSummary,
    ProjectCoverage,
    ResultsPublicationResponse,
)


@dataclass(frozen=True)
class ProgressFilters:
    track_id: str | None = None
    judge_id: str | None = None
    project_id: str | None = None
    completion_state: str | None = None
    required_reviews: int = 3


def raw_weighted_score(scorecard: Scorecard | None) -> float | None:
    if scorecard is None or not scorecard.criterion_scores:
        return None
    criteria = {criterion.id: criterion for criterion in scorecard.rubric.criteria}
    scored = [
        (item.score, criteria[item.criterion_id].weight)
        for item in scorecard.criterion_scores
        if item.criterion_id in criteria
    ]
    if not scored:
        return None
    total_weight = sum(weight for _, weight in scored)
    return round(sum(score * weight for score, weight in scored) / total_weight, 4)


def latest_scorecards(
    scorecards: list[Scorecard],
) -> dict[tuple[str, str], Scorecard]:
    latest: dict[tuple[str, str], Scorecard] = {}
    for scorecard in scorecards:
        key = (scorecard.judge_id, scorecard.project_id)
        current = latest.get(key)
        if current is None or scorecard.rubric.version > current.rubric.version:
            latest[key] = scorecard
    return latest


def protect_csv_cell(value: object | None) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


class ResultsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ResultsRepository(session)

    async def progress(
        self, event_id: str, filters: ProgressFilters
    ) -> OrganizerProgressResponse:
        if await self.repository.event(event_id) is None:
            raise ResourceNotFound("Event not found.")
        projects = await self.repository.projects(event_id)
        assignments = await self.repository.assignments(event_id)
        scorecards = await self.repository.scorecards(event_id)
        latest = latest_scorecards(scorecards)
        rows = [
            self._assignment_row(item, latest.get((item.judge_id, item.project_id)))
            for item in assignments
        ]
        rows = [
            row
            for row in rows
            if (filters.track_id is None or row.track_id == filters.track_id)
            and (filters.judge_id is None or row.judge_id == filters.judge_id)
            and (filters.project_id is None or row.project_id == filters.project_id)
            and (
                filters.completion_state is None
                or row.completion_state == filters.completion_state
            )
        ]
        visible_project_ids = {row.project_id for row in rows}
        filtered_projects = [
            project
            for project in projects
            if (filters.track_id is None or project.track_id == filters.track_id)
            and (filters.project_id is None or project.id == filters.project_id)
            and (filters.judge_id is None or project.id in visible_project_ids)
        ]
        coverage = self._coverage(
            filtered_projects, assignments, latest, filters.required_reviews
        )
        counts = Counter(row.completion_state for row in rows)
        total = len(rows)
        submitted = counts["submitted"]
        return OrganizerProgressResponse(
            summary=ProgressSummary(
                total_assignments=total,
                missing_scorecards=counts["missing"],
                draft_scorecards=counts["draft"],
                submitted_scorecards=submitted,
                completion_percentage=round(submitted * 100 / total, 1)
                if total
                else 0.0,
                insufficient_project_count=sum(
                    item.is_insufficient for item in coverage
                ),
            ),
            assignments=rows,
            projects=coverage,
        )

    async def csv_export(self, actor: User, event_id: str | None) -> str:
        event = await self.repository.event(event_id)
        if event is None:
            raise ResourceNotFound("Event not found.")
        projects = await self.repository.projects(event.id)
        assignments = await self.repository.assignments(event.id)
        latest = latest_scorecards(await self.repository.scorecards(event.id))
        by_project: dict[str, list[JudgeAssignment]] = {}
        for assignment in assignments:
            by_project.setdefault(assignment.project_id, []).append(assignment)
        submitted_counts = Counter(
            scorecard.project_id
            for scorecard in latest.values()
            if scorecard.status == "submitted"
        )
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\r\n")
        writer.writerow(
            [
                "event_id",
                "project_id",
                "project_title",
                "project_status",
                "team_id",
                "team_name",
                "track_id",
                "track_name",
                "assignment_id",
                "judge_id",
                "judge_name",
                "scorecard_id",
                "scorecard_status",
                "rubric_id",
                "rubric_version",
                "assigned_review_count",
                "submitted_review_count",
                "raw_weighted_score",
                "submitted_at",
            ]
        )
        for project in projects:
            project_assignments = by_project.get(project.id) or [None]
            for assignment in project_assignments:
                scorecard = (
                    latest.get((assignment.judge_id, project.id))
                    if assignment
                    else None
                )
                row = [
                    event.id,
                    project.id,
                    project.title,
                    project.status,
                    project.team_id,
                    project.team.name,
                    project.track_id,
                    project.track.name,
                    assignment.id if assignment else None,
                    assignment.judge_id if assignment else None,
                    assignment.judge.display_name if assignment else None,
                    scorecard.id if scorecard else None,
                    scorecard.status if scorecard else "missing",
                    scorecard.rubric_id if scorecard else None,
                    scorecard.rubric.version if scorecard else None,
                    len(by_project.get(project.id, [])),
                    submitted_counts[project.id],
                    raw_weighted_score(scorecard),
                    scorecard.submitted_at.isoformat()
                    if scorecard and scorecard.submitted_at
                    else None,
                ]
                writer.writerow([protect_csv_cell(value) for value in row])
        record_audit(
            self.session,
            action="results.exported",
            actor_id=actor.id,
            event_id=event.id,
            detail={"format": "csv", "project_count": len(projects)},
        )
        await self.session.commit()
        return output.getvalue()

    async def publish(self, actor: User, event_id: str) -> ResultsPublicationResponse:
        event = await self.repository.event(event_id)
        if event is None:
            raise ResourceNotFound("Event not found.")
        published_at = datetime.now(UTC)
        event.results_published_at = published_at
        record_audit(
            self.session,
            action="results.published",
            actor_id=actor.id,
            event_id=event.id,
            detail={"event_id": event.id, "published_at": published_at.isoformat()},
        )
        await self.session.commit()
        return ResultsPublicationResponse(event_id=event.id, published_at=published_at)

    @staticmethod
    def _assignment_row(
        assignment: JudgeAssignment, scorecard: Scorecard | None
    ) -> AssignmentProgress:
        return AssignmentProgress(
            assignment_id=assignment.id,
            judge_id=assignment.judge_id,
            judge_name=assignment.judge.display_name,
            project_id=assignment.project_id,
            project_title=assignment.project.title,
            team_id=assignment.project.team_id,
            team_name=assignment.project.team.name,
            track_id=assignment.project.track_id,
            track_name=assignment.project.track.name,
            completion_state=scorecard.status if scorecard else "missing",
            scorecard_id=scorecard.id if scorecard else None,
            rubric_version=scorecard.rubric.version if scorecard else None,
            submitted_at=scorecard.submitted_at if scorecard else None,
            raw_weighted_score=raw_weighted_score(scorecard),
        )

    @staticmethod
    def _coverage(
        projects: list[Project],
        assignments: list[JudgeAssignment],
        latest: dict[tuple[str, str], Scorecard],
        required_reviews: int,
    ) -> list[ProjectCoverage]:
        assigned = Counter(item.project_id for item in assignments)
        submitted = Counter(
            scorecard.project_id
            for scorecard in latest.values()
            if scorecard.status == "submitted"
        )
        return [
            ProjectCoverage(
                project_id=project.id,
                project_title=project.title,
                team_id=project.team_id,
                team_name=project.team.name,
                track_id=project.track_id,
                track_name=project.track.name,
                assigned_reviews=assigned[project.id],
                submitted_reviews=submitted[project.id],
                required_reviews=required_reviews,
                is_insufficient=submitted[project.id] < required_reviews,
            )
            for project in projects
        ]
