import os
import secrets

import httpx
import pytest

BASE_URL = os.getenv("JURYSTACK_TEST_BASE_URL")


def require_live() -> str:
    if not BASE_URL:
        pytest.skip("set JURYSTACK_TEST_BASE_URL to run live Tier 2 slice tests")
    return BASE_URL


@pytest.mark.asyncio
async def test_tier2_rubric_invitation_and_assignment_slice() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)
    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        invalid = await organizer.post(
            "/api/events/evt_01/rubrics",
            json={
                "criteria": [
                    {
                        "label": "Invalid",
                        "description": "Bad range",
                        "minimum_score": 5,
                        "maximum_score": 5,
                        "weight": 0,
                        "display_order": 1,
                    }
                ]
            },
        )
        assert invalid.status_code == 422
        created_rubric = await organizer.post(
            "/api/events/evt_01/rubrics",
            json={
                "criteria": [
                    {
                        "label": "Delivery",
                        "description": "How completely it works",
                        "minimum_score": 1,
                        "maximum_score": 5,
                        "weight": 3,
                        "display_order": 1,
                    },
                    {
                        "label": "Impact",
                        "description": "Who benefits",
                        "minimum_score": 0,
                        "maximum_score": 10,
                        "weight": 2,
                        "display_order": 2,
                    },
                ]
            },
        )
        assert created_rubric.status_code == 201, created_rubric.text
        history = await organizer.get("/api/events/evt_01/rubrics")
        assert history.status_code == 200
        assert len(history.json()) >= 2
        assert sum(item["is_active"] for item in history.json()) == 1
        assert any(item["version"] == 1 for item in history.json())

        duplicate = await organizer.post(
            "/api/judge-assignments",
            json={"judge_id": "jdg_01", "project_id": "prj_07"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "duplicate_assignment"
        track_violation = await organizer.post(
            "/api/judge-assignments",
            json={"judge_id": "jdg_02", "project_id": "prj_07"},
        )
        assert track_violation.status_code == 409
        assert track_violation.json()["error"]["code"] == "track_not_eligible"

        invited_email = f"judge-{suffix}@example.org"
        invite = await organizer.post(
            "/api/judge-invitations",
            json={
                "event_id": "evt_01",
                "email": invited_email,
                "track_ids": ["trk_03"],
                "expires_in_hours": 1,
            },
        )
        assert invite.status_code == 201, invite.text
        invitation_url = invite.json()["invitation_url"]
        token = invitation_url.rsplit("/", 1)[1]

    async with httpx.AsyncClient(base_url=base_url) as invited:
        preview = await invited.get(f"/api/judge-invitations/{token}")
        assert preview.status_code == 200
        accepted = await invited.post(
            f"/api/judge-invitations/{token}/accept",
            json={"display_name": "Invited Judge", "password": "long-local-password"},
        )
        assert accepted.status_code == 200, accepted.text
        judge_id = accepted.json()["id"]
        reused = await invited.post(
            f"/api/judge-invitations/{token}/accept", json={}
        )
        assert reused.status_code == 409
        assert reused.json()["error"]["code"] == "invitation_used"

    async with httpx.AsyncClient(base_url=base_url) as participant:
        participant.cookies.set("session", "prt_2e88")
        forbidden_create = await participant.post(
            "/api/judge-assignments",
            json={"judge_id": judge_id, "project_id": "prj_02"},
        )
        assert forbidden_create.status_code == 403
        forbidden_delete = await participant.delete(
            "/api/judge-assignments/not-an-assignment"
        )
        assert forbidden_delete.status_code == 403
        forbidden_balance = await participant.post(
            "/api/events/evt_01/judge-assignments/balance",
            json={"reviews_per_project": 3},
        )
        assert forbidden_balance.status_code == 403

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        manual = await organizer.post(
            "/api/judge-assignments",
            json={"judge_id": judge_id, "project_id": "prj_02"},
        )
        assert manual.status_code == 201, manual.text
        assignment_id = manual.json()["id"]
        assignments = await organizer.get(
            "/api/events/evt_01/judge-assignments"
        )
        assert assignments.status_code == 200
        assert any(item["id"] == assignment_id for item in assignments.json())
        removed = await organizer.delete(
            f"/api/judge-assignments/{assignment_id}"
        )
        assert removed.status_code == 204
        balanced = await organizer.post(
            "/api/events/evt_01/judge-assignments/balance",
            json={
                "reviews_per_project": 4,
                "project_ids": ["prj_02"],
                "judge_ids": [judge_id],
            },
        )
        assert balanced.status_code == 200, balanced.text
        assert balanced.json()["created_count"] == 1
        assert {
            (item["judge_id"], item["project_id"], item["track_id"])
            for item in balanced.json()["created"]
        } == {(judge_id, "prj_02", "trk_03")}
        balanced_again = await organizer.post(
            "/api/events/evt_01/judge-assignments/balance",
            json={
                "reviews_per_project": 4,
                "project_ids": ["prj_02"],
                "judge_ids": [judge_id],
            },
        )
        assert balanced_again.status_code == 200
        assert balanced_again.json()["created_count"] == 0

    async with httpx.AsyncClient(base_url=base_url) as judge:
        judge.cookies.set("session", "jdg_a_91bc")
        projects = await judge.get("/api/judge/projects")
        assert projects.status_code == 200
        assert projects.json()
        assert {item["track_id"] for item in projects.json()} == {"trk_03"}
