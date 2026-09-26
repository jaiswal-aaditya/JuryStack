import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine, session_factory
from app.core.fixtures import FixtureData, event_slug, load_fixture, stable_user_id
from app.core.models import (
    AuditEvent,
    CriterionScore,
    Event,
    JudgeAssignment,
    JudgeTrackEligibility,
    Project,
    Rubric,
    RubricCriterion,
    Scorecard,
    Session,
    Team,
    TeamMember,
    Track,
    User,
)

LOGGER = logging.getLogger(__name__)

DEMO_TOKENS = {
    "organizer": "org_7f2a",
    "judge_a": "jdg_a_91bc",
    "judge_b": "jdg_b_44de",
    "participant": "prt_2e88",
}
RUBRIC_ID = "rub_evt_01_v1"
CRITERIA = (
    ("functionality", "Functionality"),
    ("quality", "Quality"),
    ("innovation", "Innovation"),
)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def build_seed_rows(fixture: FixtureData) -> dict[str, list[dict[str, Any]]]:
    participant_email = fixture.teams[0].members[0].casefold()
    member_emails = sorted(
        {email.casefold() for team in fixture.teams for email in team.members}
    )
    judge_emails = {judge.email.casefold() for judge in fixture.judges}
    overlap = judge_emails.intersection(member_emails)
    if overlap:
        raise ValueError(
            f"fixture emails cannot be both judge and participant: {overlap}"
        )

    users = [
        {
            "id": "usr_organizer",
            "email": "organizer@jurystack.local",
            "display_name": "Demo Organizer",
            "role": "organizer",
            "password_hash": None,
        }
    ]
    users.extend(
        {
            "id": judge.id,
            "email": judge.email.casefold(),
            "display_name": judge.name,
            "role": "judge",
            "password_hash": None,
        }
        for judge in fixture.judges
    )
    users.extend(
        {
            "id": stable_user_id(email),
            "email": email,
            "display_name": email.partition("@")[0],
            "role": "participant",
            "password_hash": None,
        }
        for email in member_emails
    )

    event = fixture.event
    projects_by_id = {project.id: project for project in fixture.projects}
    criterion_ids = {key: f"crit_{key}" for key, _ in CRITERIA}
    expires_at = datetime(2030, 1, 1, tzinfo=UTC)
    actor_ids = {
        "organizer": "usr_organizer",
        "judge_a": fixture.judges[0].id,
        "judge_b": fixture.judges[1].id,
        "participant": stable_user_id(participant_email),
    }

    assignments = sorted({(score.judge, score.project) for score in fixture.scores})
    return {
        "users": users,
        "events": [
            {
                "id": event.id,
                "slug": event_slug(event.name),
                "name": event.name,
                "submissions_close": event.submissions_close,
            }
        ],
        "tracks": [
            {"id": track.id, "event_id": event.id, "name": track.name}
            for track in fixture.tracks
        ],
        "teams": [
            {"id": team.id, "event_id": event.id, "name": team.name}
            for team in fixture.teams
        ],
        "team_members": [
            {"team_id": team.id, "user_id": stable_user_id(email.casefold())}
            for team in fixture.teams
            for email in team.members
        ],
        "projects": [
            {
                "id": project.id,
                "event_id": event.id,
                "team_id": project.team,
                "track_id": project.track,
                "title": project.title,
                "summary": project.summary,
                "repo_url": project.repo_url,
                "status": "submitted",
                "submitted_at": project.submitted_at,
            }
            for project in fixture.projects
        ],
        "rubrics": [
            {"id": RUBRIC_ID, "event_id": event.id, "version": 1, "is_active": True}
        ],
        "rubric_criteria": [
            {
                "id": criterion_ids[key],
                "rubric_id": RUBRIC_ID,
                "key": key,
                "label": label,
                "weight": 1,
                "minimum_score": 1,
                "maximum_score": 5,
                "position": position,
            }
            for position, (key, label) in enumerate(CRITERIA, start=1)
        ],
        "judge_track_eligibility": [
            {"judge_id": judge.id, "track_id": track_id}
            for judge in fixture.judges
            for track_id in judge.tracks
        ],
        "judge_assignments": [
            {
                "id": f"asg_{judge_id}_{project_id}",
                "judge_id": judge_id,
                "project_id": project_id,
            }
            for judge_id, project_id in assignments
        ],
        "scorecards": [
            {
                "id": f"scr_{score.judge}_{score.project}",
                "judge_id": score.judge,
                "project_id": score.project,
                "rubric_id": RUBRIC_ID,
                "status": "submitted",
                "comment": score.comment,
                "submitted_at": projects_by_id[score.project].submitted_at,
            }
            for score in fixture.scores
        ],
        "criterion_scores": [
            {
                "scorecard_id": f"scr_{score.judge}_{score.project}",
                "criterion_id": criterion_ids[key],
                "score": value,
            }
            for score in fixture.scores
            for key, value in score.criteria.items()
        ],
        "sessions": [
            {
                "id": f"ses_{role}",
                "user_id": actor_ids[role],
                "token_hash": token_hash(token),
                "expires_at": expires_at,
            }
            for role, token in DEMO_TOKENS.items()
        ],
        "audit_events": [
            {
                "id": "audit_fixture_seed_v1",
                "event_id": event.id,
                "actor_id": None,
                "action": "fixtures.seeded",
                "detail": json.dumps(
                    {
                        "tracks": len(fixture.tracks),
                        "judges": len(fixture.judges),
                        "teams": len(fixture.teams),
                        "projects": len(fixture.projects),
                        "scores": len(fixture.scores),
                    },
                    sort_keys=True,
                ),
            }
        ],
    }


async def insert_rows_idempotently(
    session: AsyncSession,
    model: type[Any],
    rows: list[dict[str, Any]],
    conflict_columns: tuple[str, ...],
) -> None:
    if not rows:
        return
    statement = insert(model).values(rows)
    statement = statement.on_conflict_do_nothing(index_elements=list(conflict_columns))
    await session.execute(statement)


async def seed_database() -> dict[str, int]:
    fixture = load_fixture(settings.fixtures_path)
    rows = build_seed_rows(fixture)
    specifications = (
        (User, "users", ("id",)),
        (Event, "events", ("id",)),
        (Track, "tracks", ("id",)),
        (Team, "teams", ("id",)),
        (TeamMember, "team_members", ("team_id", "user_id")),
        (Project, "projects", ("id",)),
        (Rubric, "rubrics", ("id",)),
        (RubricCriterion, "rubric_criteria", ("id",)),
        (
            JudgeTrackEligibility,
            "judge_track_eligibility",
            ("judge_id", "track_id"),
        ),
        (JudgeAssignment, "judge_assignments", ("id",)),
        (Scorecard, "scorecards", ("id",)),
        (CriterionScore, "criterion_scores", ("scorecard_id", "criterion_id")),
        (Session, "sessions", ("id",)),
        (AuditEvent, "audit_events", ("id",)),
    )
    async with session_factory.begin() as session:
        for model, table_name, conflict_columns in specifications:
            await insert_rows_idempotently(
                session, model, rows[table_name], conflict_columns
            )

    counts = {name: len(table_rows) for name, table_rows in rows.items()}
    counts["judges"] = len(fixture.judges)
    LOGGER.info("Fixture seed complete", extra={"counts": counts})
    return counts


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    counts = await seed_database()
    print(
        "seeded fixtures: "
        f"{counts['tracks']} tracks, {counts['judges']} judges, "
        f"{counts['teams']} teams, {counts['projects']} projects, "
        f"{counts['scorecards']} score records"
    )
    print("seeded. test logins:")
    for role, token in DEMO_TOKENS.items():
        print(f"  {role:<12} Cookie: session={token}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
