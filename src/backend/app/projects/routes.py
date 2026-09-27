from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentActor, require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import Project, User
from app.projects.schemas import (
    AnswerResponse,
    GalleryResponse,
    ProjectInput,
    ProjectResponse,
)
from app.projects.service import ProjectService

router = APIRouter(tags=["projects"])
Participant = Annotated[User, Depends(require_roles(Role.PARTICIPANT))]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProjectService:
    return ProjectService(session)


def response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        event_id=project.event_id,
        team_id=project.team_id,
        team_name=project.team.name,
        track_id=project.track_id,
        track_name=project.track.name,
        title=project.title,
        summary=project.summary,
        repo_url=project.repo_url,
        status=project.status,
        submitted_at=project.submitted_at,
        custom_answers=[
            AnswerResponse(question_id=item.question_id, answer=item.answer)
            for item in project.custom_answers
        ],
    )


@router.get("/api/public/projects", response_model=GalleryResponse)
async def gallery(
    service: Annotated[ProjectService, Depends(get_service)],
    search: str | None = Query(default=None, max_length=200),
    track_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GalleryResponse:
    items, total = await service.gallery(search, track_id, limit, offset)
    return GalleryResponse(items=[response(item) for item in items], total=total)


@router.get("/api/public/projects/{project_id}", response_model=ProjectResponse)
async def public_project(
    project_id: str, service: Annotated[ProjectService, Depends(get_service)]
) -> ProjectResponse:
    return response(await service.public_detail(project_id))


@router.get("/api/projects", response_model=list[ProjectResponse])
async def my_projects(
    actor: CurrentActor, service: Annotated[ProjectService, Depends(get_service)]
) -> list[ProjectResponse]:
    return [response(item) for item in await service.mine(actor)]


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def owned_project(
    project_id: str,
    actor: CurrentActor,
    service: Annotated[ProjectService, Depends(get_service)],
) -> ProjectResponse:
    return response(await service.owned_detail(project_id, actor))


@router.post(
    "/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
async def create_project(
    payload: ProjectInput,
    actor: Participant,
    service: Annotated[ProjectService, Depends(get_service)],
) -> ProjectResponse:
    return response(await service.create(payload, actor))


@router.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectInput,
    actor: Participant,
    service: Annotated[ProjectService, Depends(get_service)],
) -> ProjectResponse:
    return response(await service.update(project_id, payload, actor))


@router.post("/api/projects/{project_id}/submit", response_model=ProjectResponse)
async def submit_project(
    project_id: str,
    actor: Participant,
    service: Annotated[ProjectService, Depends(get_service)],
) -> ProjectResponse:
    return response(await service.submit(project_id, actor))
