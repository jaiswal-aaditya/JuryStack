import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.repository import AuditRepository
from app.audit.schemas import AuditEventResponse
from app.auth.dependencies import require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import User

router = APIRouter(prefix="/api/organizer/audit-events", tags=["audit"])
Organizer = Annotated[User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))]


def get_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuditRepository:
    return AuditRepository(session)


def human_summary(action: str, detail: dict[str, object]) -> str:
    subject = next(
        (
            str(detail[key])
            for key in (
                "project_id",
                "assignment_id",
                "invitation_id",
                "rubric_id",
                "scorecard_id",
                "user_id",
            )
            if detail.get(key)
        ),
        "",
    )
    words = action.replace(".", " ").replace("_", " ")
    return f"{words}: {subject}" if subject else words


@router.get("", response_model=list[AuditEventResponse])
async def audit_history(
    _: Organizer,
    repository: Annotated[AuditRepository, Depends(get_repository)],
    event_id: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEventResponse]:
    events = await repository.list_events(
        event_id=event_id,
        actor_id=actor_id,
        action=action,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )
    responses = []
    for item in events:
        detail = json.loads(item.detail)
        responses.append(
            AuditEventResponse(
                id=item.id,
                event_id=item.event_id,
                actor_id=item.actor_id,
                actor_name=item.actor.display_name if item.actor else None,
                action=item.action,
                summary=human_summary(item.action, detail),
                detail=detail,
                occurred_at=item.occurred_at,
            )
        )
    return responses
