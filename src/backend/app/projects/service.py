import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.roles import Role
from app.core.errors import Conflict, InvalidRequest, PermissionDenied, ResourceNotFound
from app.core.models import CustomQuestion, Event, Project, Team, Track, User
from app.projects.repository import ProjectRepository
from app.projects.schemas import ProjectInput


def require_deadline_open(event: Event, now: datetime) -> None:
    if now >= event.submissions_close:
        raise Conflict(
            "deadline_closed",
            f"Submissions closed at {event.submissions_close.isoformat()}.",
        )
    if event.submissions_open and now < event.submissions_open:
        raise Conflict(
            "submissions_not_open",
            f"Submissions open at {event.submissions_open.isoformat()}.",
        )


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.session = session
        self.repository = ProjectRepository(session)
        self.now = now

    async def gallery(
        self, search: str | None, track_id: str | None, limit: int, offset: int
    ) -> tuple[list[Project], int]:
        return await self.repository.gallery(search, track_id, limit, offset)

    async def public_detail(self, project_id: str) -> Project:
        project = await self._get(project_id)
        if project.status != "submitted":
            raise ResourceNotFound("Project not found.")
        return project

    async def mine(self, actor: User) -> list[Project]:
        return await self.repository.mine(actor.id)

    async def owned_detail(self, project_id: str, actor: User) -> Project:
        project = await self._get(project_id)
        await self._authorize(project.team_id, actor)
        return project

    async def create(self, payload: ProjectInput, actor: User) -> Project:
        team = await self._resolve_team(payload, actor)
        event = await self._resolve_event(payload, team)
        require_deadline_open(event, self.now())
        track = await self._resolve_track(payload.track_id, event)
        project = Project(
            id=f"prj_{secrets.token_hex(10)}",
            event_id=event.id,
            team_id=team.id,
            track_id=track.id,
            title=payload.title.strip(),
            summary=payload.summary.strip(),
            repo_url=payload.repo_url,
            status="draft",
            submitted_at=None,
        )
        self.session.add(project)
        await self.session.flush()
        project = await self._get(project.id)
        await self._apply(project, payload)
        if payload.submit:
            await self._submit(project)
        record_audit(
            self.session,
            action="project.created",
            actor_id=actor.id,
            event_id=event.id,
            detail={"project_id": project.id, "status": project.status},
        )
        await self.session.commit()
        return await self._get(project.id)

    async def update(
        self, project_id: str, payload: ProjectInput, actor: User
    ) -> Project:
        project = await self._get(project_id)
        await self._authorize(project.team_id, actor)
        require_deadline_open(project.event, self.now())
        if payload.team_id and payload.team_id != project.team_id:
            raise InvalidRequest(
                "team_cannot_change", "A project's team cannot change."
            )
        if payload.event_id and payload.event_id != project.event_id:
            raise InvalidRequest(
                "event_cannot_change", "A project's event cannot change."
            )
        track = await self._resolve_track(
            payload.track_id or project.track_id, project.event
        )
        project.track_id = track.id
        await self._apply(project, payload)
        if payload.submit and project.status != "submitted":
            await self._submit(project)
        record_audit(
            self.session,
            action="project.updated",
            actor_id=actor.id,
            event_id=project.event_id,
            detail={"project_id": project.id, "status": project.status},
        )
        await self.session.commit()
        return await self._get(project.id)

    async def submit(self, project_id: str, actor: User) -> Project:
        project = await self._get(project_id)
        await self._authorize(project.team_id, actor)
        require_deadline_open(project.event, self.now())
        await self._submit(project)
        record_audit(
            self.session,
            action="project.submitted",
            actor_id=actor.id,
            event_id=project.event_id,
            detail={"project_id": project.id},
        )
        await self.session.commit()
        return await self._get(project.id)

    async def _get(self, project_id: str) -> Project:
        project = await self.repository.by_id(project_id)
        if project is None:
            raise ResourceNotFound("Project not found.")
        return project

    async def _authorize(self, team_id: str, actor: User) -> None:
        if actor.role in {Role.ORGANIZER, Role.ADMIN}:
            return
        if actor.role != Role.PARTICIPANT or not await self.repository.is_member(
            team_id, actor.id
        ):
            raise PermissionDenied("Only members of this team may edit the project.")

    async def _resolve_team(self, payload: ProjectInput, actor: User) -> Team:
        team = (
            await self.session.get(Team, payload.team_id)
            if payload.team_id
            else await self.repository.first_team(actor.id)
        )
        if team is None:
            raise InvalidRequest("team_required", "Create or select a team first.")
        await self._authorize(team.id, actor)
        return team

    async def _resolve_event(self, payload: ProjectInput, team: Team) -> Event:
        if payload.event_id and payload.event_id != team.event_id:
            raise InvalidRequest("event_mismatch", "The team belongs to another event.")
        event = await self.session.get(Event, team.event_id)
        assert event is not None
        return event

    async def _resolve_track(self, track_id: str | None, event: Event) -> Track:
        track = (
            await self.session.get(Track, track_id)
            if track_id
            else await self.session.scalar(
                select(Track).where(Track.event_id == event.id).order_by(Track.id)
            )
        )
        if track is None or track.event_id != event.id:
            raise InvalidRequest("invalid_track", "Select a track from this event.")
        return track

    async def _apply(self, project: Project, payload: ProjectInput) -> None:
        project.title = payload.title.strip()
        project.summary = payload.summary.strip()
        project.repo_url = payload.repo_url
        answers = {
            item.question_id: item.answer.strip() for item in payload.custom_answers
        }
        if len(answers) != len(payload.custom_answers):
            raise InvalidRequest(
                "duplicate_answer", "Each question may be answered once."
            )
        allowed_ids = set(
            (
                await self.session.scalars(
                    select(CustomQuestion.id).where(
                        CustomQuestion.event_id == project.event_id
                    )
                )
            ).all()
        )
        if set(answers) - allowed_ids:
            raise InvalidRequest(
                "invalid_question", "An answer references another event."
            )
        await self.repository.replace_answers(project, answers)

    async def _submit(self, project: Project) -> None:
        if not project.repo_url:
            raise InvalidRequest("repo_url_required", "A repository URL is required.")
        required = set(
            (
                await self.session.scalars(
                    select(CustomQuestion.id).where(
                        CustomQuestion.event_id == project.event_id,
                        CustomQuestion.required.is_(True),
                    )
                )
            ).all()
        )
        present = {
            answer.question_id
            for answer in project.custom_answers
            if answer.answer.strip()
        }
        if missing := required - present:
            raise InvalidRequest(
                "required_answers_missing",
                f"Answer all required questions ({len(missing)} missing).",
            )
        if project.status == "submitted":
            raise Conflict("already_submitted", "This project is already submitted.")
        project.status = "submitted"
        project.submitted_at = self.now()
