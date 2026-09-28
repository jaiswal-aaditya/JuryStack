from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import User
from app.results.schemas import (
    OrganizerProgressResponse,
    RankingResponse,
    ResultsPublicationResponse,
)
from app.results.service import ProgressFilters, ResultsService

router = APIRouter(prefix="/api/organizer", tags=["results"])
Organizer = Annotated[User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ResultsService:
    return ResultsService(session)


@router.get("/events/{event_id}/progress", response_model=OrganizerProgressResponse)
async def progress(
    event_id: str,
    _: Organizer,
    service: Annotated[ResultsService, Depends(get_service)],
    track_id: str | None = None,
    judge_id: str | None = None,
    project_id: str | None = None,
    completion_state: Literal["missing", "draft", "submitted"] | None = None,
    required_reviews: int = Query(default=3, ge=1, le=20),
) -> OrganizerProgressResponse:
    return await service.progress(
        event_id,
        ProgressFilters(
            track_id=track_id,
            judge_id=judge_id,
            project_id=project_id,
            completion_state=completion_state,
            required_reviews=required_reviews,
        ),
    )


@router.get(
    "/events/{event_id}/rankings",
    response_model=RankingResponse,
)
async def rankings(
    event_id: str,
    _: Organizer,
    service: Annotated[ResultsService, Depends(get_service)],
    minimum_reviews: int = Query(default=2, ge=1, le=20),
    minimum_overlap: int = Query(default=2, ge=1, le=20),
) -> RankingResponse:
    return await service.rankings(
        event_id,
        minimum_reviews=minimum_reviews,
        minimum_overlap=minimum_overlap,
    )


@router.get("/results.csv")
async def results_csv(
    actor: Organizer,
    service: Annotated[ResultsService, Depends(get_service)],
    event_id: str | None = None,
) -> Response:
    body = await service.csv_export(actor, event_id)
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jurystack-results.csv"'},
    )


@router.post(
    "/events/{event_id}/results/publish",
    response_model=ResultsPublicationResponse,
)
async def publish_results(
    event_id: str,
    actor: Organizer,
    service: Annotated[ResultsService, Depends(get_service)],
) -> ResultsPublicationResponse:
    return await service.publish(actor, event_id)
