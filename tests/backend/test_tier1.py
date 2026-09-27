from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.errors import Conflict
from app.core.models import Event
from app.events.schemas import EventInput
from app.projects.schemas import ProjectInput
from app.projects.service import require_deadline_open
from app.teams.service import TeamService, hash_invite_token


def event(close: datetime, open_at: datetime | None = None) -> Event:
    return Event(
        id="evt_test",
        slug="test",
        name="Test",
        starts_at=None,
        submissions_open=open_at,
        submissions_close=close,
    )


def test_event_dates_must_be_ordered_and_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        EventInput.model_validate(
            {
                "name": "Invalid",
                "slug": "invalid",
                "submissions_open": "2026-10-02T00:00:00Z",
                "submissions_close": "2026-10-01T00:00:00Z",
                "tracks": [{"name": "General"}],
            }
        )
    with pytest.raises(ValidationError):
        EventInput.model_validate(
            {
                "name": "Naive",
                "slug": "naive",
                "submissions_close": "2026-10-01T00:00:00",
                "tracks": [{"name": "General"}],
            }
        )


def test_project_repository_url_requires_http_origin() -> None:
    with pytest.raises(ValidationError):
        ProjectInput.model_validate(
            {"title": "Unsafe", "summary": "URL", "repo_url": "javascript:alert(1)"}
        )
    with pytest.raises(ValidationError):
        ProjectInput.model_validate(
            {"title": "Incomplete", "summary": "URL", "repo_url": "https:repo"}
        )


def test_deadline_boundary_is_closed_at_the_exact_instant() -> None:
    close = datetime(2026, 10, 1, tzinfo=UTC)
    require_deadline_open(event(close), close - timedelta(microseconds=1))
    with pytest.raises(Conflict) as error:
        require_deadline_open(event(close), close)
    assert error.value.code == "deadline_closed"


def test_submission_open_boundary_is_inclusive() -> None:
    opens = datetime(2026, 9, 30, tzinfo=UTC)
    close = datetime(2026, 10, 1, tzinfo=UTC)
    with pytest.raises(Conflict) as error:
        require_deadline_open(event(close, opens), opens - timedelta(microseconds=1))
    assert error.value.code == "submissions_not_open"
    require_deadline_open(event(close, opens), opens)


@pytest.mark.asyncio
async def test_expired_invite_is_rejected_without_becoming_membership() -> None:
    class ExpiredInviteRepository:
        async def valid_invite(self, token_hash: str, now: datetime) -> None:
            assert token_hash == hash_invite_token("expired-token")
            assert now.tzinfo is not None
            return None

        async def expired_or_used_invite(self, token_hash: str) -> bool:
            assert token_hash == hash_invite_token("expired-token")
            return True

    service = TeamService(object())  # type: ignore[arg-type]
    service.repository = ExpiredInviteRepository()  # type: ignore[assignment]
    actor = type("Actor", (), {"id": "usr_test"})()

    with pytest.raises(Conflict) as error:
        await service.accept_invite("expired-token", actor)  # type: ignore[arg-type]

    assert error.value.code == "invite_expired"
