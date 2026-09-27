import asyncio
import hashlib
import secrets
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.security import hash_password
from app.core.errors import Conflict, InvalidRequest, PermissionDenied, ResourceNotFound
from app.core.models import (
    CriterionScore,
    JudgeAssignment,
    JudgeInvitation,
    JudgeInvitationTrack,
    JudgeTrackEligibility,
    Project,
    Rubric,
    RubricCriterion,
    Scorecard,
    User,
)
from app.judging.repository import JudgingRepository
from app.judging.schemas import (
    AssignmentCreate,
    BalancedAssignmentCreate,
    CriterionInput,
    JudgeInvitationAccept,
    JudgeInvitationCreate,
    RubricCreate,
    ScorecardDraftInput,
)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def plan_balanced_assignments(
    projects: list[tuple[str, str]],
    judge_tracks: dict[str, set[str]],
    existing: set[tuple[str, str]],
    reviews_per_project: int,
) -> list[tuple[str, str]]:
    """Return deterministic, track-safe assignments or fail without partial work."""
    load = Counter(judge_id for judge_id, _ in existing)
    assigned_by_project: dict[str, set[str]] = defaultdict(set)
    for judge_id, project_id in existing:
        assigned_by_project[project_id].add(judge_id)

    planned: list[tuple[str, str]] = []
    for project_id, track_id in sorted(projects):
        assigned = assigned_by_project[project_id]
        while len(assigned) < reviews_per_project:
            eligible = [
                judge_id
                for judge_id, tracks in judge_tracks.items()
                if track_id in tracks and judge_id not in assigned
            ]
            if not eligible:
                raise Conflict(
                    "insufficient_eligible_judges",
                    f"Project {project_id} does not have enough eligible judges.",
                )
            chosen = min(eligible, key=lambda judge_id: (load[judge_id], judge_id))
            assigned.add(chosen)
            load[chosen] += 1
            planned.append((chosen, project_id))
    return planned


class JudgingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = JudgingRepository(session)

    async def _event(self, event_id: str):
        event = await self.repository.event(event_id)
        if event is None:
            raise ResourceNotFound("Event not found.")
        return event

    async def rubrics(self, event_id: str) -> list[Rubric]:
        await self._event(event_id)
        return await self.repository.rubrics(event_id)

    async def create_rubric(
        self, event_id: str, payload: RubricCreate, actor: User
    ) -> Rubric:
        await self._event(event_id)
        version = await self.repository.next_rubric_version(event_id)
        await self.session.execute(
            update(Rubric)
            .where(Rubric.event_id == event_id, Rubric.is_active.is_(True))
            .values(is_active=False)
        )
        rubric = Rubric(
            id=f"rub_{secrets.token_hex(12)}",
            event_id=event_id,
            version=version,
            is_active=True,
        )
        rubric.criteria = [
            self._criterion(rubric.id, item, position)
            for position, item in enumerate(
                sorted(payload.criteria, key=lambda item: item.display_order), start=1
            )
        ]
        self.session.add(rubric)
        record_audit(
            self.session,
            action="rubric.version_created",
            actor_id=actor.id,
            event_id=event_id,
            detail={
                "rubric_id": rubric.id,
                "version": version,
                "criterion_count": len(rubric.criteria),
            },
        )
        await self._commit("rubric_conflict", "The rubric could not be saved.")
        return next(
            item
            for item in await self.repository.rubrics(event_id)
            if item.id == rubric.id
        )

    @staticmethod
    def _criterion(
        rubric_id: str, item: CriterionInput, position: int
    ) -> RubricCriterion:
        return RubricCriterion(
            id=f"crit_{secrets.token_hex(12)}",
            rubric_id=rubric_id,
            key=f"criterion_{position}",
            label=item.label.strip(),
            description=item.description.strip(),
            weight=item.weight,
            minimum_score=item.minimum_score,
            maximum_score=item.maximum_score,
            position=item.display_order,
        )

    async def create_invitation(
        self, payload: JudgeInvitationCreate, actor: User
    ) -> tuple[JudgeInvitation, str]:
        event = await self._event(payload.event_id)
        requested = set(payload.track_ids)
        if len(requested) != len(payload.track_ids):
            raise Conflict("duplicate_tracks", "Invitation tracks must be unique.")
        event_tracks = {track.id for track in event.tracks}
        if not requested.issubset(event_tracks):
            raise Conflict(
                "track_event_mismatch",
                "Every invitation track must belong to the event.",
            )
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        invitation = JudgeInvitation(
            id=f"jiv_{secrets.token_hex(10)}",
            event_id=event.id,
            email=payload.email,
            token_hash=hash_invitation_token(token),
            expires_at=expires_at,
        )
        invitation.tracks = [
            JudgeInvitationTrack(track_id=track_id) for track_id in sorted(requested)
        ]
        self.session.add(invitation)
        record_audit(
            self.session,
            action="judge.invitation_created",
            actor_id=actor.id,
            event_id=event.id,
            detail={
                "invitation_id": invitation.id,
                "email": invitation.email,
                "track_ids": sorted(requested),
                "expires_at": expires_at.isoformat(),
            },
        )
        await self._commit(
            "invitation_conflict", "The invitation could not be created."
        )
        return invitation, token

    async def invitations(self, event_id: str) -> list[JudgeInvitation]:
        await self._event(event_id)
        return await self.repository.invitations(event_id)

    async def invitation(self, token: str) -> JudgeInvitation:
        invitation = await self.repository.invitation_by_token(
            hash_invitation_token(token)
        )
        self._require_available_invitation(invitation)
        assert invitation is not None
        return invitation

    @staticmethod
    def _require_available_invitation(
        invitation: JudgeInvitation | None,
    ) -> None:
        if invitation is None:
            raise ResourceNotFound("Judge invitation not found.")
        if invitation.accepted_by_user_id is not None:
            raise Conflict("invitation_used", "This judge invitation was already used.")
        if invitation.expires_at <= datetime.now(UTC):
            raise Conflict("invitation_expired", "This judge invitation has expired.")

    async def accept_invitation(
        self,
        token: str,
        payload: JudgeInvitationAccept,
        actor: User | None,
    ) -> User:
        invitation = await self.repository.invitation_by_token(
            hash_invitation_token(token), lock=True
        )
        self._require_available_invitation(invitation)
        assert invitation is not None
        user = await self.repository.user_by_email(invitation.email)
        if user is not None:
            if actor is None or actor.id != user.id:
                raise PermissionDenied(
                    "Sign in with the invited email before accepting this invitation."
                )
            if user.role in {"organizer", "admin"}:
                raise Conflict(
                    "role_conflict",
                    "Organizer and admin accounts cannot become judges.",
                )
            user.role = "judge"
        else:
            if payload.display_name is None or payload.password is None:
                raise Conflict(
                    "account_details_required",
                    "A display name and password are required for a new local judge.",
                )
            user = User(
                id=f"usr_{secrets.token_hex(12)}",
                email=invitation.email,
                display_name=payload.display_name.strip(),
                role="judge",
                password_hash=await asyncio.to_thread(hash_password, payload.password),
            )
            self.session.add(user)
            await self.session.flush()
        for invitation_track in invitation.tracks:
            if not await self.repository.eligible(user.id, invitation_track.track_id):
                self.session.add(
                    JudgeTrackEligibility(
                        judge_id=user.id, track_id=invitation_track.track_id
                    )
                )
        invitation.accepted_by_user_id = user.id
        record_audit(
            self.session,
            action="judge.invitation_accepted",
            actor_id=user.id,
            event_id=invitation.event_id,
            detail={"invitation_id": invitation.id, "judge_id": user.id},
        )
        await self._commit("invitation_used", "This judge invitation was already used.")
        return user

    async def judges(self, event_id: str) -> list[User]:
        await self._event(event_id)
        return await self.repository.judges(event_id)

    async def assignments(self, event_id: str) -> list[JudgeAssignment]:
        await self._event(event_id)
        return await self.repository.assignments(event_id)

    async def create_assignment(
        self, payload: AssignmentCreate, actor: User
    ) -> JudgeAssignment:
        project = await self.repository.project(payload.project_id)
        if project is None:
            raise ResourceNotFound("Project not found.")
        if project.status != "submitted":
            raise Conflict(
                "project_not_submitted",
                "Only submitted projects can be assigned.",
            )
        judge = await self.session.get(User, payload.judge_id)
        if judge is None or judge.role != "judge":
            raise ResourceNotFound("Judge not found.")
        if not await self.repository.eligible(judge.id, project.track_id):
            raise Conflict(
                "track_not_eligible",
                "The judge is not eligible for this project track.",
            )
        if await self.repository.assignment_pair(judge.id, project.id):
            raise Conflict("duplicate_assignment", "This assignment already exists.")
        assignment = JudgeAssignment(
            id=f"asg_{secrets.token_hex(14)}",
            judge_id=judge.id,
            project_id=project.id,
        )
        self.session.add(assignment)
        record_audit(
            self.session,
            action="judge.assignment_created",
            actor_id=actor.id,
            event_id=project.event_id,
            detail={
                "assignment_id": assignment.id,
                "judge_id": judge.id,
                "project_id": project.id,
            },
        )
        await self._commit("duplicate_assignment", "This assignment already exists.")
        found = await self.repository.assignment(assignment.id)
        assert found is not None
        return found

    async def delete_assignment(self, assignment_id: str, actor: User) -> None:
        assignment = await self.repository.assignment(assignment_id)
        if assignment is None:
            raise ResourceNotFound("Assignment not found.")
        if await self.repository.scorecard_exists(
            assignment.judge_id, assignment.project_id
        ):
            raise Conflict(
                "assignment_has_scorecard",
                "Assignments with scorecards cannot be removed.",
            )
        event_id = assignment.project.event_id
        await self.session.delete(assignment)
        record_audit(
            self.session,
            action="judge.assignment_deleted",
            actor_id=actor.id,
            event_id=event_id,
            detail={"assignment_id": assignment_id},
        )
        await self.session.commit()

    async def balance(
        self, event_id: str, payload: BalancedAssignmentCreate, actor: User
    ) -> list[JudgeAssignment]:
        await self._event(event_id)
        projects = await self.repository.projects(event_id)
        if payload.project_ids is not None:
            requested_projects = set(payload.project_ids)
            projects = [item for item in projects if item.id in requested_projects]
            if {item.id for item in projects} != requested_projects:
                raise Conflict(
                    "project_event_mismatch",
                    "Every selected project must be a submitted project in the event.",
                )
        judges = await self.repository.judges(event_id)
        if payload.judge_ids is not None:
            requested_judges = set(payload.judge_ids)
            judges = [item for item in judges if item.id in requested_judges]
            if {item.id for item in judges} != requested_judges:
                raise Conflict(
                    "judge_event_mismatch",
                    "Every selected judge must be eligible in the event.",
                )
        if not projects:
            raise Conflict("no_projects", "There are no submitted projects to assign.")
        if not judges:
            raise Conflict("no_judges", "There are no eligible judges to assign.")
        existing_models = await self.repository.assignments(event_id)
        existing = {
            (item.judge_id, item.project_id) for item in existing_models
        }
        judge_tracks = {
            judge.id: {
                eligibility.track_id for eligibility in judge.track_eligibilities
            }
            for judge in judges
        }
        planned = plan_balanced_assignments(
            [(project.id, project.track_id) for project in projects],
            judge_tracks,
            existing,
            payload.reviews_per_project,
        )
        created_ids: list[str] = []
        for judge_id, project_id in planned:
            assignment = JudgeAssignment(
                id=f"asg_{secrets.token_hex(14)}",
                judge_id=judge_id,
                project_id=project_id,
            )
            created_ids.append(assignment.id)
            self.session.add(assignment)
        record_audit(
            self.session,
            action="judge.assignments_balanced",
            actor_id=actor.id,
            event_id=event_id,
            detail={
                "reviews_per_project": payload.reviews_per_project,
                "created_count": len(planned),
            },
        )
        await self._commit(
            "assignment_conflict", "Assignments changed while the batch was created."
        )
        assignments = await self.repository.assignments(event_id)
        created_set = set(created_ids)
        return [item for item in assignments if item.id in created_set]

    async def judge_projects(self, actor: User) -> list[Project]:
        return await self.repository.judge_projects(actor.id)

    async def judge_scorecards(
        self, actor: User, requested_judge_id: str | None = None
    ) -> list[Scorecard]:
        if requested_judge_id is not None and requested_judge_id != actor.id:
            raise PermissionDenied("Judges cannot access another judge's scorecards.")
        return await self.repository.judge_scorecards(actor.id)

    async def scorecard_detail(self, scorecard_id: str, actor: User) -> Scorecard:
        scorecard = await self.repository.judge_scorecard(actor.id, scorecard_id)
        if scorecard is None:
            raise ResourceNotFound("Scorecard not found.")
        return scorecard

    async def scorecard_workspace(
        self, project_id: str, actor: User
    ) -> tuple[Project, Rubric, Scorecard | None]:
        project = await self._assigned_project(actor.id, project_id)
        scorecards = await self.repository.judge_project_scorecards(
            actor.id, project.id
        )
        drafts = [item for item in scorecards if item.status == "draft"]
        if drafts:
            scorecard = max(drafts, key=lambda item: item.rubric.version)
            return project, scorecard.rubric, scorecard
        rubric = await self.repository.active_rubric(project.event_id)
        if rubric is None:
            raise Conflict(
                "rubric_unavailable", "No active rubric is available for this event."
            )
        active_scorecard = next(
            (item for item in scorecards if item.rubric_id == rubric.id), None
        )
        return project, rubric, active_scorecard

    async def save_scorecard_draft(
        self, project_id: str, payload: ScorecardDraftInput, actor: User
    ) -> Scorecard:
        project = await self._assigned_project(actor.id, project_id)
        rubric = await self.repository.rubric(payload.rubric_id)
        if rubric is None or rubric.event_id != project.event_id:
            raise InvalidRequest(
                "rubric_unavailable", "The rubric is unavailable for this project."
            )
        scorecard = await self.repository.judge_project_rubric_scorecard(
            actor.id, project.id, rubric.id, lock=True
        )
        if scorecard is None:
            if not rubric.is_active:
                raise Conflict(
                    "rubric_not_active",
                    "Reload the scorecard before starting this rubric version.",
                )
            scorecard = Scorecard(
                id=f"scr_{secrets.token_hex(16)}",
                judge_id=actor.id,
                project_id=project.id,
                rubric_id=rubric.id,
                status="draft",
                comment="",
                submitted_at=None,
            )
            scorecard.rubric = rubric
            scorecard.project = project
            scorecard.judge = actor
            self.session.add(scorecard)
        elif scorecard.status == "submitted":
            raise Conflict(
                "scorecard_submitted", "Submitted scorecards cannot be edited."
            )

        values = self._validated_scores(rubric, payload)
        scorecard.comment = payload.comment.strip()
        scorecard.criterion_scores = [
            CriterionScore(
                scorecard_id=scorecard.id,
                criterion_id=criterion_id,
                score=score,
            )
            for criterion_id, score in values.items()
        ]
        await self._commit(
            "scorecard_conflict", "The scorecard changed while it was being saved."
        )
        saved = await self.repository.judge_scorecard(actor.id, scorecard.id)
        assert saved is not None
        return saved

    async def submit_scorecard(self, scorecard_id: str, actor: User) -> Scorecard:
        scorecard = await self.repository.judge_scorecard(
            actor.id, scorecard_id, lock=True
        )
        if scorecard is None:
            raise ResourceNotFound("Scorecard not found.")
        if scorecard.status == "submitted":
            raise Conflict(
                "scorecard_submitted", "This scorecard was already submitted."
            )
        expected = {item.id for item in scorecard.rubric.criteria}
        actual = {item.criterion_id for item in scorecard.criterion_scores}
        if actual != expected:
            raise Conflict(
                "scorecard_incomplete",
                "Every rubric criterion must be scored before submission.",
            )
        scorecard.status = "submitted"
        scorecard.submitted_at = datetime.now(UTC)
        record_audit(
            self.session,
            action="judge.scorecard_submitted",
            actor_id=actor.id,
            event_id=scorecard.project.event_id,
            detail={
                "scorecard_id": scorecard.id,
                "judge_id": actor.id,
                "project_id": scorecard.project_id,
                "rubric_id": scorecard.rubric_id,
            },
        )
        await self._commit(
            "scorecard_conflict", "The scorecard changed while it was submitted."
        )
        submitted = await self.repository.judge_scorecard(actor.id, scorecard.id)
        assert submitted is not None
        return submitted

    async def organizer_scorecards(self, event_id: str) -> list[Scorecard]:
        await self._event(event_id)
        return await self.repository.organizer_scorecards(event_id)

    async def organizer_progress(
        self, event_id: str
    ) -> tuple[list[JudgeAssignment], list[Scorecard]]:
        await self._event(event_id)
        return (
            await self.repository.assignments(event_id),
            await self.repository.organizer_scorecards(event_id),
        )

    async def _assigned_project(self, judge_id: str, project_id: str) -> Project:
        project = await self.repository.assigned_project(judge_id, project_id)
        if project is None:
            raise PermissionDenied("The project is not assigned to this judge.")
        return project

    @staticmethod
    def _validated_scores(
        rubric: Rubric, payload: ScorecardDraftInput
    ) -> dict[str, int]:
        criteria = {item.id: item for item in rubric.criteria}
        values: dict[str, int] = {}
        for item in payload.scores:
            criterion = criteria.get(item.criterion_id)
            if criterion is None:
                raise InvalidRequest(
                    "criterion_mismatch",
                    "Every score must belong to the selected rubric.",
                )
            if not criterion.minimum_score <= item.score <= criterion.maximum_score:
                raise InvalidRequest(
                    "score_out_of_range",
                    f"{criterion.label} must be between "
                    f"{criterion.minimum_score} and {criterion.maximum_score}.",
                )
            values[item.criterion_id] = item.score
        return values

    async def _commit(self, code: str, message: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise Conflict(code, message) from error
