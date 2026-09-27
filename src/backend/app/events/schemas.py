from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TrackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)


class PrizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    prompt: str = Field(min_length=1, max_length=2000)
    required: bool = False


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    starts_at: datetime | None = None
    submissions_open: datetime | None = None
    submissions_close: datetime
    tracks: list[TrackInput] = Field(min_length=1, max_length=50)
    prizes: list[PrizeInput] = Field(default_factory=list, max_length=50)
    custom_questions: list[QuestionInput] = Field(default_factory=list, max_length=50)

    @field_validator("starts_at", "submissions_open", "submissions_close")
    @classmethod
    def require_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Dates must include a UTC offset.")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> "EventInput":
        if self.starts_at and self.submissions_open:
            if self.starts_at > self.submissions_open:
                raise ValueError("starts_at must not be after submissions_open")
        if self.submissions_open and self.submissions_open >= self.submissions_close:
            raise ValueError("submissions_open must be before submissions_close")
        if len({track.name.casefold() for track in self.tracks}) != len(self.tracks):
            raise ValueError("Track names must be unique within an event.")
        return self


class TrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str


class PrizeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    prompt: str
    position: int
    required: bool


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    name: str
    starts_at: datetime | None
    submissions_open: datetime | None
    submissions_close: datetime
    tracks: list[TrackResponse]
    prizes: list[PrizeResponse]
    custom_questions: list[QuestionResponse]
