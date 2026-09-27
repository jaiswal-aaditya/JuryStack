from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    event_id: str | None
    actor_id: str | None
    actor_name: str | None
    action: str
    summary: str
    detail: dict[str, object]
    occurred_at: datetime
