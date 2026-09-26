import hashlib
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictFixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventFixture(StrictFixtureModel):
    id: str
    name: str
    submissions_close: datetime


class TrackFixture(StrictFixtureModel):
    id: str
    name: str


class JudgeFixture(StrictFixtureModel):
    id: str
    name: str
    email: str
    tracks: list[str]


class TeamFixture(StrictFixtureModel):
    id: str
    name: str
    members: list[str]


class ProjectFixture(StrictFixtureModel):
    id: str
    team: str
    track: str
    title: str
    summary: str
    repo_url: str
    submitted_at: datetime


class ScoreFixture(StrictFixtureModel):
    judge: str
    project: str
    criteria: dict[str, int]
    comment: str

    @model_validator(mode="after")
    def validate_criteria(self) -> "ScoreFixture":
        expected = {"functionality", "quality", "innovation"}
        if set(self.criteria) != expected:
            raise ValueError(f"criteria must be exactly {sorted(expected)}")
        if any(score < 1 or score > 5 for score in self.criteria.values()):
            raise ValueError("criterion scores must be between 1 and 5")
        return self


class FixtureData(StrictFixtureModel):
    event: EventFixture
    tracks: list[TrackFixture]
    judges: list[JudgeFixture]
    teams: list[TeamFixture]
    projects: list[ProjectFixture]
    scores: list[ScoreFixture]

    @model_validator(mode="after")
    def validate_references(self) -> "FixtureData":
        track_ids = {track.id for track in self.tracks}
        judge_ids = {judge.id for judge in self.judges}
        team_ids = {team.id for team in self.teams}
        project_ids = {project.id for project in self.projects}

        if any(set(judge.tracks) - track_ids for judge in self.judges):
            raise ValueError("judge references an unknown track")
        if any(project.team not in team_ids for project in self.projects):
            raise ValueError("project references an unknown team")
        if any(project.track not in track_ids for project in self.projects):
            raise ValueError("project references an unknown track")
        if any(score.judge not in judge_ids for score in self.scores):
            raise ValueError("score references an unknown judge")
        if any(score.project not in project_ids for score in self.scores):
            raise ValueError("score references an unknown project")
        return self


class SeedData(StrictFixtureModel):
    tables: dict[str, list[dict[str, object]]] = Field(default_factory=dict)


def load_fixture(path: Path) -> FixtureData:
    return FixtureData.model_validate_json(path.read_text(encoding="utf-8"))


def stable_user_id(email: str) -> str:
    digest = hashlib.sha256(email.casefold().encode()).hexdigest()[:20]
    return f"usr_{digest}"


def event_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug or "event"
