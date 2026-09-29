from datetime import datetime

from pydantic import BaseModel


class VotingWindowUpsert(BaseModel):
    opens_at: datetime
    closes_at: datetime
    is_enabled: bool = True


class VotingWindowResponse(BaseModel):
    id: str
    event_id: str
    opens_at: datetime
    closes_at: datetime
    is_enabled: bool


class VoterInvitationCreate(BaseModel):
    email: str
    expires_in_hours: int = 168


class VoterInvitationResponse(BaseModel):
    id: str
    event_id: str
    email: str
    expires_at: datetime
    invitation_url: str | None = None


class BallotEntryResponse(BaseModel):
    project_id: str
    title: str
    summary: str
    track_name: str
    position: int


class BallotResponse(BaseModel):
    id: str
    event_id: str
    entries: list[BallotEntryResponse]
    has_voted: bool


class VoteCreate(BaseModel):
    project_id: str


class VoteResponse(BaseModel):
    id: str
    project_id: str
    cast_at: datetime