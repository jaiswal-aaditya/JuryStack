from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriterionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    minimum_score: int = Field(ge=0, le=99)
    maximum_score: int = Field(ge=1, le=100)
    weight: int = Field(ge=1, le=1000)
    display_order: int = Field(ge=1, le=100)

    @field_validator("label")
    @classmethod
    def nonempty_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Criterion label cannot be blank.")
        return value

    @model_validator(mode="after")
    def valid_range(self) -> "CriterionInput":
        if self.minimum_score >= self.maximum_score:
            raise ValueError("minimum_score must be less than maximum_score")
        return self


class RubricCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criteria: list[CriterionInput] = Field(min_length=1, max_length=25)

    @model_validator(mode="after")
    def unique_criteria(self) -> "RubricCreate":
        labels = [item.label.strip().casefold() for item in self.criteria]
        positions = [item.display_order for item in self.criteria]
        if len(set(labels)) != len(labels):
            raise ValueError("Criterion labels must be unique.")
        if len(set(positions)) != len(positions):
            raise ValueError("Criterion display_order values must be unique.")
        return self


class CriterionResponse(BaseModel):
    id: str
    label: str
    description: str
    minimum_score: int
    maximum_score: int
    weight: int
    display_order: int


class RubricResponse(BaseModel):
    id: str
    event_id: str
    version: int
    is_active: bool
    criteria: list[CriterionResponse]


class JudgeInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    email: str = Field(min_length=3, max_length=320)
    track_ids: list[str] = Field(min_length=1, max_length=50)
    expires_in_hours: int = Field(default=24, ge=1, le=168)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized.count("@") != 1 or "." not in normalized.partition("@")[2]:
            raise ValueError("A valid email address is required.")
        return normalized


class JudgeInvitationResponse(BaseModel):
    id: str
    event_id: str
    email: str
    track_ids: list[str]
    expires_at: datetime
    accepted_by_user_id: str | None
    invitation_url: str | None = None


class JudgeInvitationPreview(BaseModel):
    event_id: str
    event_name: str
    email: str
    track_names: list[str]
    expires_at: datetime


class JudgeInvitationAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=12, max_length=200)

    @field_validator("display_name")
    @classmethod
    def nonempty_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be blank.")
        return value


class JudgeResponse(BaseModel):
    id: str
    email: str
    display_name: str
    track_ids: list[str]


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judge_id: str
    project_id: str


class AssignmentResponse(BaseModel):
    id: str
    event_id: str
    judge_id: str
    judge_name: str
    project_id: str
    project_title: str
    track_id: str
    track_name: str


class BalancedAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviews_per_project: int = Field(ge=1, le=20)
    project_ids: list[str] | None = Field(default=None, max_length=500)
    judge_ids: list[str] | None = Field(default=None, max_length=500)


class BalancedAssignmentResponse(BaseModel):
    created: list[AssignmentResponse]
    created_count: int


class JudgeProjectResponse(BaseModel):
    id: str
    event_id: str
    title: str
    summary: str
    repo_url: str
    track_id: str
    track_name: str
    submitted_at: datetime | None


class CriterionScoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str
    score: int = Field(ge=0, le=100)


class ScorecardDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rubric_id: str
    scores: list[CriterionScoreInput] = Field(default_factory=list, max_length=25)
    comment: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def unique_criteria(self) -> "ScorecardDraftInput":
        criterion_ids = [item.criterion_id for item in self.scores]
        if len(set(criterion_ids)) != len(criterion_ids):
            raise ValueError("Criterion scores must be unique.")
        return self


class ScoreCriterionResponse(BaseModel):
    criterion_id: str
    label: str
    description: str
    minimum_score: int
    maximum_score: int
    weight: int
    display_order: int
    score: int | None


class ScorecardResponse(BaseModel):
    id: str
    judge_id: str
    project_id: str
    project_title: str
    event_id: str
    track_id: str
    track_name: str
    rubric_id: str
    rubric_version: int
    status: str
    comment: str
    submitted_at: datetime | None
    criteria: list[ScoreCriterionResponse]


class ScorecardWorkspaceResponse(BaseModel):
    project: JudgeProjectResponse
    rubric: RubricResponse
    scorecard: ScorecardResponse | None


class OrganizerScorecardResponse(ScorecardResponse):
    judge_name: str


class JudgingProgressResponse(BaseModel):
    assignment_id: str
    judge_id: str
    judge_name: str
    project_id: str
    project_title: str
    track_id: str
    track_name: str
    status: str
    rubric_version: int | None
    submitted_at: datetime | None
