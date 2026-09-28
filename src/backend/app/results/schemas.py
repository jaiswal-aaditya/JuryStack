from datetime import datetime

from pydantic import BaseModel


class AssignmentProgress(BaseModel):
    assignment_id: str
    judge_id: str
    judge_name: str
    project_id: str
    project_title: str
    team_id: str
    team_name: str
    track_id: str
    track_name: str
    completion_state: str
    scorecard_id: str | None
    rubric_version: int | None
    submitted_at: datetime | None
    raw_weighted_score: float | None


class ProjectCoverage(BaseModel):
    project_id: str
    project_title: str
    team_id: str
    team_name: str
    track_id: str
    track_name: str
    assigned_reviews: int
    submitted_reviews: int
    required_reviews: int
    is_insufficient: bool


class ProgressSummary(BaseModel):
    total_assignments: int
    missing_scorecards: int
    draft_scorecards: int
    submitted_scorecards: int
    completion_percentage: float
    insufficient_project_count: int


class OrganizerProgressResponse(BaseModel):
    summary: ProgressSummary
    assignments: list[AssignmentProgress]
    projects: list[ProjectCoverage]


class ResultsPublicationResponse(BaseModel):
    event_id: str
    published_at: datetime


class JudgeCalibrationResponse(BaseModel):
    judge_id: str
    judge_name: str
    eligible_review_count: int
    overlap_count: int
    raw_variance: float
    bias: float
    fallback_used: str


class ReviewContributionResponse(BaseModel):
    review_id: str
    judge_id: str
    judge_name: str
    raw_weighted_total: float
    raw_percentage: float
    judge_bias: float
    normalized_contribution: float
    fallback_used: str


class ProjectRankingResponse(BaseModel):
    project_id: str
    project_title: str
    team_id: str
    team_name: str
    track_id: str
    track_name: str
    eligible: bool
    eligibility_reason: str | None
    review_count: int
    excluded_review_count: int
    raw_total: float | None
    final_value: float | None
    raw_rank: int | None
    rank: int | None
    rank_movement: int | None
    fallbacks_used: list[str]
    contributions: list[ReviewContributionResponse]


class RankingResponse(BaseModel):
    method: str
    formula_version: str
    minimum_reviews: int
    minimum_overlap: int
    projects: list[ProjectRankingResponse]
    judges: list[JudgeCalibrationResponse]
