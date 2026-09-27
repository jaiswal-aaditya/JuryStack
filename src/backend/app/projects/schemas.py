from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    answer: str = Field(max_length=10000)


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str | None = None
    team_id: str | None = None
    track_id: str | None = None
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=10000)
    repo_url: str = Field(default="", max_length=2000)
    custom_answers: list[AnswerInput] = Field(default_factory=list, max_length=50)
    submit: bool = False

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if value and (parsed.scheme not in {"http", "https"} or not parsed.netloc):
            raise ValueError("Repository URL must use http or https.")
        return value


class AnswerResponse(BaseModel):
    question_id: str
    answer: str


class ProjectResponse(BaseModel):
    id: str
    event_id: str
    team_id: str
    team_name: str
    track_id: str
    track_name: str
    title: str
    summary: str
    repo_url: str
    status: str
    submitted_at: datetime | None
    custom_answers: list[AnswerResponse]


class GalleryResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
