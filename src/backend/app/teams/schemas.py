from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    name: str = Field(min_length=1, max_length=200)


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    display_name: str


class TeamResponse(BaseModel):
    id: str
    event_id: str
    name: str
    members: list[MemberResponse]


class InviteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_in_hours: int = Field(default=24, ge=1, le=168)


class InviteResponse(BaseModel):
    token: str
    expires_at: datetime
