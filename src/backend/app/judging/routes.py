from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_optional_actor, require_roles
from app.auth.roles import Role
from app.core.database import get_database_session
from app.core.models import (
    JudgeAssignment,
    JudgeInvitation,
    Project,
    Rubric,
    Scorecard,
    User,
)
from app.judging.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    BalancedAssignmentCreate,
    BalancedAssignmentResponse,
    CriterionResponse,
    JudgeInvitationAccept,
    JudgeInvitationCreate,
    JudgeInvitationPreview,
    JudgeInvitationResponse,
    JudgeProjectResponse,
    JudgeResponse,
    JudgingProgressResponse,
    OrganizerScorecardResponse,
    RubricCreate,
    RubricResponse,
    ScorecardDraftInput,
    ScorecardResponse,
    ScorecardWorkspaceResponse,
    ScoreCriterionResponse,
)
from app.judging.service import JudgingService

router = APIRouter(prefix="/api", tags=["judging"])
Organizer = Annotated[User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))]
Judge = Annotated[User, Depends(require_roles(Role.JUDGE))]
OptionalActor = Annotated[User | None, Depends(get_optional_actor)]


def get_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> JudgingService:
    return JudgingService(session)


def rubric_response(rubric: Rubric) -> RubricResponse:
    return RubricResponse(
        id=rubric.id,
        event_id=rubric.event_id,
        version=rubric.version,
        is_active=rubric.is_active,
        criteria=[
            CriterionResponse(
                id=item.id,
                label=item.label,
                description=item.description,
                minimum_score=item.minimum_score,
                maximum_score=item.maximum_score,
                weight=item.weight,
                display_order=item.position,
            )
            for item in sorted(rubric.criteria, key=lambda item: item.position)
        ],
    )


def invitation_response(
    invitation: JudgeInvitation, invitation_url: str | None = None
) -> JudgeInvitationResponse:
    return JudgeInvitationResponse(
        id=invitation.id,
        event_id=invitation.event_id,
        email=invitation.email,
        track_ids=sorted(item.track_id for item in invitation.tracks),
        expires_at=invitation.expires_at,
        accepted_by_user_id=invitation.accepted_by_user_id,
        invitation_url=invitation_url,
    )


def assignment_response(assignment: JudgeAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=assignment.id,
        event_id=assignment.project.event_id,
        judge_id=assignment.judge_id,
        judge_name=assignment.judge.display_name,
        project_id=assignment.project_id,
        project_title=assignment.project.title,
        track_id=assignment.project.track_id,
        track_name=assignment.project.track.name,
    )


def project_response(project: Project) -> JudgeProjectResponse:
    return JudgeProjectResponse(
        id=project.id,
        event_id=project.event_id,
        title=project.title,
        summary=project.summary,
        repo_url=project.repo_url,
        track_id=project.track_id,
        track_name=project.track.name,
        submitted_at=project.submitted_at,
    )


def scorecard_response(scorecard: Scorecard) -> ScorecardResponse:
    values = {item.criterion_id: item.score for item in scorecard.criterion_scores}
    return ScorecardResponse(
        id=scorecard.id,
        judge_id=scorecard.judge_id,
        project_id=scorecard.project_id,
        project_title=scorecard.project.title,
        event_id=scorecard.project.event_id,
        track_id=scorecard.project.track_id,
        track_name=scorecard.project.track.name,
        rubric_id=scorecard.rubric_id,
        rubric_version=scorecard.rubric.version,
        status=scorecard.status,
        comment=scorecard.comment,
        submitted_at=scorecard.submitted_at,
        criteria=[
            ScoreCriterionResponse(
                criterion_id=item.id,
                label=item.label,
                description=item.description,
                minimum_score=item.minimum_score,
                maximum_score=item.maximum_score,
                weight=item.weight,
                display_order=item.position,
                score=values.get(item.id),
            )
            for item in sorted(
                scorecard.rubric.criteria, key=lambda item: item.position
            )
        ],
    )


def organizer_scorecard_response(scorecard: Scorecard) -> OrganizerScorecardResponse:
    response = scorecard_response(scorecard)
    return OrganizerScorecardResponse(
        **response.model_dump(), judge_name=scorecard.judge.display_name
    )


@router.get("/events/{event_id}/rubrics", response_model=list[RubricResponse])
async def list_rubrics(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[RubricResponse]:
    return [rubric_response(item) for item in await service.rubrics(event_id)]


@router.post(
    "/events/{event_id}/rubrics",
    response_model=RubricResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rubric(
    event_id: str,
    payload: RubricCreate,
    actor: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> RubricResponse:
    return rubric_response(await service.create_rubric(event_id, payload, actor))


@router.get(
    "/events/{event_id}/judge-invitations",
    response_model=list[JudgeInvitationResponse],
)
async def list_invitations(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[JudgeInvitationResponse]:
    return [
        invitation_response(item) for item in await service.invitations(event_id)
    ]


@router.post(
    "/judge-invitations",
    response_model=JudgeInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: JudgeInvitationCreate,
    actor: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> JudgeInvitationResponse:
    invitation, token = await service.create_invitation(payload, actor)
    return invitation_response(invitation, f"/judge-invitations/{token}")


@router.get(
    "/judge-invitations/{token}", response_model=JudgeInvitationPreview
)
async def preview_invitation(
    token: str,
    service: Annotated[JudgingService, Depends(get_service)],
) -> JudgeInvitationPreview:
    invitation = await service.invitation(token)
    return JudgeInvitationPreview(
        event_id=invitation.event_id,
        event_name=invitation.event.name,
        email=invitation.email,
        track_names=[item.track.name for item in invitation.tracks],
        expires_at=invitation.expires_at,
    )


@router.post(
    "/judge-invitations/{token}/accept",
    response_model=JudgeResponse,
)
async def accept_invitation(
    token: str,
    payload: JudgeInvitationAccept,
    actor: OptionalActor,
    service: Annotated[JudgingService, Depends(get_service)],
) -> JudgeResponse:
    invitation = await service.invitation(token)
    track_ids = sorted(item.track_id for item in invitation.tracks)
    judge = await service.accept_invitation(token, payload, actor)
    return JudgeResponse(
        id=judge.id,
        email=judge.email,
        display_name=judge.display_name,
        track_ids=track_ids,
    )


@router.get("/events/{event_id}/judges", response_model=list[JudgeResponse])
async def list_judges(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[JudgeResponse]:
    event = await service.repository.event(event_id)
    event_track_ids = {item.id for item in event.tracks} if event else set()
    return [
        JudgeResponse(
            id=judge.id,
            email=judge.email,
            display_name=judge.display_name,
            track_ids=sorted(
                item.track_id
                for item in judge.track_eligibilities
                if item.track_id in event_track_ids
            ),
        )
        for judge in await service.judges(event_id)
    ]


@router.get(
    "/events/{event_id}/judge-assignments",
    response_model=list[AssignmentResponse],
)
async def list_assignments(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[AssignmentResponse]:
    return [
        assignment_response(item) for item in await service.assignments(event_id)
    ]


@router.post(
    "/judge-assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    payload: AssignmentCreate,
    actor: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> AssignmentResponse:
    return assignment_response(await service.create_assignment(payload, actor))


@router.delete(
    "/judge-assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_assignment(
    assignment_id: str,
    actor: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> Response:
    await service.delete_assignment(assignment_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/events/{event_id}/judge-assignments/balance",
    response_model=BalancedAssignmentResponse,
)
async def balance_assignments(
    event_id: str,
    payload: BalancedAssignmentCreate,
    actor: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> BalancedAssignmentResponse:
    created = await service.balance(event_id, payload, actor)
    responses = [assignment_response(item) for item in created]
    return BalancedAssignmentResponse(created=responses, created_count=len(responses))


@router.get("/judge/projects", response_model=list[JudgeProjectResponse])
async def list_judge_projects(
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[JudgeProjectResponse]:
    return [project_response(item) for item in await service.judge_projects(actor)]


@router.get("/judge/scores", response_model=list[ScorecardResponse])
@router.get("/judge/scorecards", response_model=list[ScorecardResponse])
async def list_judge_scorecards(
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
    judge_id: str | None = None,
) -> list[ScorecardResponse]:
    scorecards = await service.judge_scorecards(actor, judge_id)
    return [scorecard_response(item) for item in scorecards]


@router.get(
    "/judge/scorecards/{scorecard_id}", response_model=ScorecardResponse
)
async def judge_scorecard_detail(
    scorecard_id: str,
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
) -> ScorecardResponse:
    return scorecard_response(await service.scorecard_detail(scorecard_id, actor))


@router.get(
    "/judge/projects/{project_id}/scorecard",
    response_model=ScorecardWorkspaceResponse,
)
async def judge_scorecard_workspace(
    project_id: str,
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
) -> ScorecardWorkspaceResponse:
    project, rubric, scorecard = await service.scorecard_workspace(project_id, actor)
    return ScorecardWorkspaceResponse(
        project=project_response(project),
        rubric=rubric_response(rubric),
        scorecard=scorecard_response(scorecard) if scorecard else None,
    )


@router.put(
    "/judge/projects/{project_id}/scorecard", response_model=ScorecardResponse
)
async def save_judge_scorecard_draft(
    project_id: str,
    payload: ScorecardDraftInput,
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
) -> ScorecardResponse:
    return scorecard_response(
        await service.save_scorecard_draft(project_id, payload, actor)
    )


@router.post(
    "/judge/scorecards/{scorecard_id}/submit", response_model=ScorecardResponse
)
async def submit_judge_scorecard(
    scorecard_id: str,
    actor: Judge,
    service: Annotated[JudgingService, Depends(get_service)],
) -> ScorecardResponse:
    return scorecard_response(await service.submit_scorecard(scorecard_id, actor))


@router.get(
    "/organizer/events/{event_id}/scorecards",
    response_model=list[OrganizerScorecardResponse],
)
async def organizer_scorecards(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[OrganizerScorecardResponse]:
    return [
        organizer_scorecard_response(item)
        for item in await service.organizer_scorecards(event_id)
    ]


@router.get(
    "/organizer/events/{event_id}/judging-progress",
    response_model=list[JudgingProgressResponse],
)
async def organizer_judging_progress(
    event_id: str,
    _: Organizer,
    service: Annotated[JudgingService, Depends(get_service)],
) -> list[JudgingProgressResponse]:
    assignments, scorecards = await service.organizer_progress(event_id)
    latest: dict[tuple[str, str], Scorecard] = {}
    for scorecard in scorecards:
        key = (scorecard.judge_id, scorecard.project_id)
        current = latest.get(key)
        if current is None or scorecard.rubric.version > current.rubric.version:
            latest[key] = scorecard
    return [
        JudgingProgressResponse(
            assignment_id=assignment.id,
            judge_id=assignment.judge_id,
            judge_name=assignment.judge.display_name,
            project_id=assignment.project_id,
            project_title=assignment.project.title,
            track_id=assignment.project.track_id,
            track_name=assignment.project.track.name,
            status=(
                latest[(assignment.judge_id, assignment.project_id)].status
                if (assignment.judge_id, assignment.project_id) in latest
                else "not_started"
            ),
            rubric_version=(
                latest[(assignment.judge_id, assignment.project_id)].rubric.version
                if (assignment.judge_id, assignment.project_id) in latest
                else None
            ),
            submitted_at=(
                latest[(assignment.judge_id, assignment.project_id)].submitted_at
                if (assignment.judge_id, assignment.project_id) in latest
                else None
            ),
        )
        for assignment in assignments
    ]
