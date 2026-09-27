import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.errors import ResourceNotFound
from app.core.models import JudgeAssignment, Project, Scorecard, User
from app.results.normalization import (
    CriterionValue,
    ReviewInput,
    normalize_rankings,
    score_review,
)
from app.results.repository import ResultsRepository
from app.results.schemas import (
    AssignmentProgress,
    JudgeCalibrationResponse,
    OrganizerProgressResponse,
    ProgressSummary,
    ProjectCoverage,
    ProjectRankingResponse,
    RankingResponse,
    ResultsPublicationResponse,
    ReviewContributionResponse,
)


@dataclass(frozen=True)
class ProgressFilters:
    track_id: str | None = None
    judge_id: str | None = None
    project_id: str | None = None
    completion_state: str | None = None
    required_reviews: int = 3


def raw_weighted_score(scorecard: Scorecard | None) -> float | None:
    if scorecard is None:
        return None
    return score_review(review_input(scorecard)).raw_percentage


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


def review_input(scorecard: Scorecard) -> ReviewInput:
    values = {item.criterion_id: item.score for item in scorecard.criterion_scores}
    return ReviewInput(
        review_id=scorecard.id,
        judge_id=scorecard.judge_id,
        project_id=scorecard.project_id,
        status=scorecard.status,
        criteria=tuple(
            CriterionValue(
                criterion_id=criterion.id,
                score=values.get(criterion.id),
                minimum_score=criterion.minimum_score,
                maximum_score=criterion.maximum_score,
                weight=criterion.weight,
            )
            for criterion in sorted(
                scorecard.rubric.criteria, key=lambda item: item.position
            )
        ),
    )


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
        normalized = normalize_rankings(
            [review_input(item) for item in latest.values()],
            [project.id for project in projects],
        )
        ranking_by_project = {item.project_id: item for item in normalized.projects}
        contribution_by_review = {
            item.review_id: item
            for project in normalized.projects
            for item in project.contributions
        }
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
                "raw_weighted_total",
                "raw_percentage",
                "judge_bias",
                "normalized_contribution",
                "normalization_fallback",
                "project_final_value",
                "project_rank",
                "rank_movement",
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
                contribution = (
                    contribution_by_review.get(scorecard.id) if scorecard else None
                )
                ranking = ranking_by_project[project.id]
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
                    contribution.raw_weighted_total if contribution else None,
                    contribution.raw_percentage if contribution else None,
                    contribution.judge_bias if contribution else None,
                    contribution.normalized_contribution if contribution else None,
                    contribution.fallback_used if contribution else None,
                    ranking.final_value,
                    ranking.rank,
                    ranking.rank_movement,
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

    async def rankings(
        self,
        event_id: str,
        *,
        minimum_reviews: int = 2,
        minimum_overlap: int = 2,
    ) -> RankingResponse:
        if await self.repository.event(event_id) is None:
            raise ResourceNotFound("Event not found.")
        projects = await self.repository.projects(event_id)
        latest = latest_scorecards(await self.repository.scorecards(event_id))
        result = normalize_rankings(
            [review_input(item) for item in latest.values()],
            [project.id for project in projects],
            minimum_reviews=minimum_reviews,
            minimum_overlap=minimum_overlap,
        )
        project_by_id = {project.id: project for project in projects}
        judge_names = {
            item.judge_id: item.judge.display_name
            for item in await self.repository.assignments(event_id)
        }
        return RankingResponse(
            method="paired_overlap_median_bias",
            formula_version="1.0",
            minimum_reviews=minimum_reviews,
            minimum_overlap=minimum_overlap,
            projects=[
                ProjectRankingResponse(
                    project_id=item.project_id,
                    project_title=project_by_id[item.project_id].title,
                    team_id=project_by_id[item.project_id].team_id,
                    team_name=project_by_id[item.project_id].team.name,
                    track_id=project_by_id[item.project_id].track_id,
                    track_name=project_by_id[item.project_id].track.name,
                    eligible=item.eligible,
                    eligibility_reason=item.eligibility_reason,
                    review_count=item.review_count,
                    excluded_review_count=item.excluded_review_count,
                    raw_total=item.raw_total,
                    final_value=item.final_value,
                    raw_rank=item.raw_rank,
                    rank=item.rank,
                    rank_movement=item.rank_movement,
                    fallbacks_used=list(item.fallbacks_used),
                    contributions=[
                        ReviewContributionResponse(
                            review_id=contribution.review_id,
                            judge_id=contribution.judge_id,
                            judge_name=judge_names.get(
                                contribution.judge_id, contribution.judge_id
                            ),
                            raw_weighted_total=contribution.raw_weighted_total,
                            raw_percentage=contribution.raw_percentage,
                            judge_bias=contribution.judge_bias,
                            normalized_contribution=(
                                contribution.normalized_contribution
                            ),
                            fallback_used=contribution.fallback_used,
                        )
                        for contribution in item.contributions
                    ],
                )
                for item in result.projects
            ],
            judges=[
                JudgeCalibrationResponse(
                    judge_id=item.judge_id,
                    judge_name=judge_names.get(item.judge_id, item.judge_id),
                    eligible_review_count=item.eligible_review_count,
                    overlap_count=item.overlap_count,
                    raw_variance=item.raw_variance,
                    bias=item.bias,
                    fallback_used=item.fallback_used,
                )
                for item in result.judges
            ],
        )

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
