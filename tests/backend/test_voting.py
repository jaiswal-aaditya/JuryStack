import asyncio
import os
import secrets

import httpx
import pytest
import pytest_asyncio

BASE_URL = os.getenv("JURYSTACK_TEST_BASE_URL")


def require_live() -> str:
    if not BASE_URL:
        pytest.skip("set JURYSTACK_TEST_BASE_URL to run live voting tests")
    return BASE_URL


async def _set_window(
    client: httpx.AsyncClient, *, opens_at: str, closes_at: str
) -> None:
    response = await client.put(
        "/api/events/evt_01/voting-window",
        json={"opens_at": opens_at, "closes_at": closes_at, "is_enabled": True},
    )
    assert response.status_code == 200, response.text


async def _open_window(client: httpx.AsyncClient) -> None:
    await _set_window(
        client,
        opens_at="2020-01-01T00:00:00Z",
        closes_at="2030-01-01T00:00:00Z",
    )


async def _invite_voter(client: httpx.AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/events/evt_01/voter-invitations",
        json={"email": email},
    )
    assert response.status_code == 201, response.text
    invitation_url = response.json()["invitation_url"]
    assert invitation_url is not None
    return invitation_url.rsplit("/", 1)[-1]


@pytest_asyncio.fixture(autouse=True)
async def _restore_open_window():
    yield
    if not BASE_URL:
        return
    async with httpx.AsyncClient(base_url=BASE_URL) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)


@pytest.mark.asyncio
async def test_full_voting_lifecycle_and_duplicate_rejection() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)
        token = await _invite_voter(organizer, f"voter_{suffix}@example.org")

    async with httpx.AsyncClient(base_url=base_url) as voter:
        first = await voter.get(f"/api/voting/{token}/ballot")
        assert first.status_code == 200, first.text
        ballot = first.json()
        assert ballot["has_voted"] is False
        assert len(ballot["entries"]) > 0

        second = await voter.get(f"/api/voting/{token}/ballot")
        assert second.status_code == 200
        assert second.json()["id"] == ballot["id"]
        assert [item["position"] for item in second.json()["entries"]] == [
            item["position"] for item in ballot["entries"]
        ]
        assert [item["project_id"] for item in second.json()["entries"]] == [
            item["project_id"] for item in ballot["entries"]
        ]

        chosen_project = ballot["entries"][0]["project_id"]
        cast = await voter.post(
            f"/api/voting/{token}/vote", json={"project_id": chosen_project}
        )
        assert cast.status_code == 200, cast.text
        assert cast.json()["project_id"] == chosen_project

        duplicate = await voter.post(
            f"/api/voting/{token}/vote",
            json={"project_id": ballot["entries"][1]["project_id"]},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "already_voted"

        refreshed = await voter.get(f"/api/voting/{token}/ballot")
        assert refreshed.status_code == 200
        assert refreshed.json()["has_voted"] is True


@pytest.mark.asyncio
async def test_concurrent_duplicate_votes_only_one_succeeds() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)
        token = await _invite_voter(organizer, f"race_{suffix}@example.org")

    async with httpx.AsyncClient(base_url=base_url) as voter:
        ballot = (await voter.get(f"/api/voting/{token}/ballot")).json()
        project_a = ballot["entries"][0]["project_id"]
        project_b = ballot["entries"][1]["project_id"]

    async def cast(project_id: str) -> httpx.Response:
        async with httpx.AsyncClient(base_url=base_url) as client:
            return await client.post(
                f"/api/voting/{token}/vote", json={"project_id": project_id}
            )

    results = await asyncio.gather(
        cast(project_a), cast(project_b), return_exceptions=True
    )
    statuses = sorted(
        response.status_code
        for response in results
        if isinstance(response, httpx.Response)
    )
    assert statuses == [200, 409]

    async with httpx.AsyncClient(base_url=base_url) as voter:
        final = await voter.get(f"/api/voting/{token}/ballot")
        assert final.json()["has_voted"] is True


@pytest.mark.asyncio
async def test_expired_invitation_is_rejected() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)
        response = await organizer.post(
            "/api/events/evt_01/voter-invitations",
            json={"email": f"expired_{suffix}@example.org", "expires_in_hours": -1},
        )
        assert response.status_code == 201, response.text
        token = response.json()["invitation_url"].rsplit("/", 1)[-1]

    async with httpx.AsyncClient(base_url=base_url) as voter:
        result = await voter.get(f"/api/voting/{token}/ballot")
        assert result.status_code == 409
        assert result.json()["error"]["code"] == "invitation_expired"


@pytest.mark.asyncio
async def test_project_not_on_ballot_is_rejected() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)
        token = await _invite_voter(organizer, f"badproject_{suffix}@example.org")

    async with httpx.AsyncClient(base_url=base_url) as voter:
        await voter.get(f"/api/voting/{token}/ballot")
        result = await voter.post(
            f"/api/voting/{token}/vote", json={"project_id": "not_a_real_project"}
        )
        assert result.status_code == 400
        assert result.json()["error"]["code"] == "project_not_on_ballot"


@pytest.mark.asyncio
async def test_voting_before_window_opens_is_rejected() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _set_window(
            organizer,
            opens_at="2030-01-01T00:00:00Z",
            closes_at="2031-01-01T00:00:00Z",
        )
        token = await _invite_voter(organizer, f"early_{suffix}@example.org")

    async with httpx.AsyncClient(base_url=base_url) as voter:
        result = await voter.get(f"/api/voting/{token}/ballot")
        assert result.status_code == 409
        assert result.json()["error"]["code"] == "voting_closed"


@pytest.mark.asyncio
async def test_voting_after_window_closes_is_rejected() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _open_window(organizer)
        token = await _invite_voter(organizer, f"late_{suffix}@example.org")

    async with httpx.AsyncClient(base_url=base_url) as voter:
        opened = await voter.get(f"/api/voting/{token}/ballot")
        assert opened.status_code == 200, opened.text

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        await _set_window(
            organizer,
            opens_at="2020-01-01T00:00:00Z",
            closes_at="2020-06-01T00:00:00Z",
        )

    async with httpx.AsyncClient(base_url=base_url) as voter:
        chosen_project = opened.json()["entries"][0]["project_id"]
        result = await voter.post(
            f"/api/voting/{token}/vote", json={"project_id": chosen_project}
        )
        assert result.status_code == 409
        assert result.json()["error"]["code"] == "voting_closed"


@pytest.mark.asyncio
async def test_unknown_token_is_not_found() -> None:
    base_url = require_live()

    async with httpx.AsyncClient(base_url=base_url) as voter:
        ballot_result = await voter.get("/api/voting/not-a-real-token/ballot")
        assert ballot_result.status_code == 404

        vote_result = await voter.post(
            "/api/voting/not-a-real-token/vote", json={"project_id": "prj_01"}
        )
        assert vote_result.status_code == 404


@pytest.mark.asyncio
async def test_non_organizer_cannot_manage_voting_setup() -> None:
    base_url = require_live()

    async with httpx.AsyncClient(base_url=base_url) as judge:
        judge.cookies.set("session", "jdg_a_91bc")
        window_attempt = await judge.put(
            "/api/events/evt_01/voting-window",
            json={
                "opens_at": "2020-01-01T00:00:00Z",
                "closes_at": "2030-01-01T00:00:00Z",
                "is_enabled": True,
            },
        )
        assert window_attempt.status_code == 403

        invitation_attempt = await judge.post(
            "/api/events/evt_01/voter-invitations",
            json={"email": "sneaky@example.org"},
        )
        assert invitation_attempt.status_code == 403

    async with httpx.AsyncClient(base_url=base_url) as participant:
        participant.cookies.set("session", "prt_2e88")
        participant_attempt = await participant.post(
            "/api/events/evt_01/voter-invitations",
            json={"email": "sneaky2@example.org"},
        )
        assert participant_attempt.status_code == 403