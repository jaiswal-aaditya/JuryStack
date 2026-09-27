import os
import secrets
from datetime import UTC, datetime, timedelta

import httpx
import pytest

BASE_URL = os.getenv("JURYSTACK_TEST_BASE_URL")


def require_live() -> str:
    if not BASE_URL:
        pytest.skip("set JURYSTACK_TEST_BASE_URL to run live Tier 1 tests")
    return BASE_URL


async def login(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "jurystack-local-demo"},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_complete_tier1_api_flow_and_adversarial_paths() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)
    now = datetime.now(UTC)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        invalid = await organizer.post(
            "/api/events",
            json={
                "name": "Invalid",
                "slug": f"invalid-{suffix}",
                "submissions_open": (now + timedelta(days=2)).isoformat(),
                "submissions_close": (now + timedelta(days=1)).isoformat(),
                "tracks": [{"name": "General"}],
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "validation_error"
        created = await organizer.post(
            "/api/events",
            json={
                "name": f"T1 Flow {suffix}",
                "slug": f"t1-flow-{suffix}",
                "starts_at": (now - timedelta(hours=2)).isoformat(),
                "submissions_open": (now - timedelta(hours=1)).isoformat(),
                "submissions_close": (now + timedelta(days=1)).isoformat(),
                "tracks": [
                    {"name": "General"},
                    {"name": "Accessibility"},
                ],
                "prizes": [{"name": "Best demo", "description": "Clarity"}],
                "custom_questions": [{"prompt": "Who benefits?", "required": True}],
            },
        )
        assert created.status_code == 201, created.text
        event = created.json()
        edited = await organizer.put(
            f"/api/events/{event['id']}",
            json={
                "name": f"T1 Flow edited {suffix}",
                "slug": event["slug"],
                "starts_at": event["starts_at"],
                "submissions_open": event["submissions_open"],
                "submissions_close": event["submissions_close"],
                "tracks": [
                    {"id": item["id"], "name": item["name"]} for item in event["tracks"]
                ],
                "prizes": [
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "description": item["description"],
                    }
                    for item in event["prizes"]
                ],
                "custom_questions": [
                    {
                        "id": item["id"],
                        "prompt": item["prompt"],
                        "required": item["required"],
                    }
                    for item in event["custom_questions"]
                ],
            },
        )
        assert edited.status_code == 200, edited.text
        event = edited.json()
        assert event["name"] == f"T1 Flow edited {suffix}"

    async with httpx.AsyncClient(base_url=base_url) as owner:
        await login(owner, "priya1@example.org")
        team_response = await owner.post(
            "/api/teams", json={"event_id": event["id"], "name": f"Team {suffix}"}
        )
        assert team_response.status_code == 201, team_response.text
        team = team_response.json()
        invite_response = await owner.post(
            f"/api/teams/{team['id']}/invites", json={"expires_in_hours": 1}
        )
        assert invite_response.status_code == 200
        token = invite_response.json()["token"]

        draft_response = await owner.post(
            "/api/projects",
            json={
                "event_id": event["id"],
                "team_id": team["id"],
                "track_id": event["tracks"][0]["id"],
                "title": f"Searchable {suffix}",
                "summary": "A complete Tier 1 flow",
                "repo_url": "https://example.org/t1",
                "custom_answers": [],
            },
        )
        assert draft_response.status_code == 201, draft_response.text
        draft = draft_response.json()
        missing = await owner.post(f"/api/projects/{draft['id']}/submit")
        assert missing.status_code == 400
        assert missing.json()["error"]["code"] == "required_answers_missing"
        updated = await owner.put(
            f"/api/projects/{draft['id']}",
            json={
                "title": draft["title"],
                "summary": draft["summary"],
                "repo_url": draft["repo_url"],
                "track_id": draft["track_id"],
                "custom_answers": [
                    {
                        "question_id": event["custom_questions"][0]["id"],
                        "answer": "Local communities",
                    }
                ],
                "submit": True,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "submitted"
        assert updated.json()["submitted_at"] is not None
        assert updated.json()["custom_answers"][0]["answer"] == "Local communities"

    async with httpx.AsyncClient(base_url=base_url) as teammate:
        await login(teammate, "lena2@example.org")
        forbidden_invite = await teammate.post(
            f"/api/teams/{team['id']}/invites", json={"expires_in_hours": 1}
        )
        assert forbidden_invite.status_code == 403
        accepted = await teammate.post(f"/api/team-invites/{token}/accept")
        assert accepted.status_code == 200, accepted.text
        reused = await teammate.post(f"/api/team-invites/{token}/accept")
        assert reused.status_code == 404

    async with httpx.AsyncClient(base_url=base_url) as stranger:
        await login(stranger, "sofia3@example.org")
        forbidden_edit = await stranger.put(
            f"/api/projects/{draft['id']}",
            json={
                "title": "Stolen",
                "summary": "No",
                "repo_url": "https://example.org/no",
            },
        )
        assert forbidden_edit.status_code == 403

    async with httpx.AsyncClient(base_url=base_url) as public:
        by_search = await public.get("/api/public/projects", params={"search": suffix})
        assert by_search.status_code == 200
        assert [item["id"] for item in by_search.json()["items"]] == [draft["id"]]
        by_track = await public.get(
            "/api/public/projects",
            params={"track_id": event["tracks"][1]["id"]},
        )
        assert by_track.status_code == 200
        assert by_track.json()["items"] == []
        detail = await public.get(f"/api/public/projects/{draft['id']}")
        assert detail.status_code == 200


@pytest.mark.asyncio
async def test_closed_fixture_rejects_direct_participant_create() -> None:
    base_url = require_live()
    async with httpx.AsyncClient(base_url=base_url) as client:
        client.cookies.set("session", "prt_2e88")
        response = await client.post(
            "/api/projects",
            json={"title": "late", "summary": "direct API probe"},
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "deadline_closed"
