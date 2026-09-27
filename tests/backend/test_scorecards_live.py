import os
import secrets

import httpx
import pytest

BASE_URL = os.getenv("JURYSTACK_TEST_BASE_URL")


def require_live() -> str:
    if not BASE_URL:
        pytest.skip("set JURYSTACK_TEST_BASE_URL to run live scorecard tests")
    return BASE_URL


@pytest.mark.asyncio
async def test_private_scorecard_lifecycle_and_adversarial_isolation() -> None:
    base_url = require_live()
    suffix = secrets.token_hex(4)

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        rubric_response = await organizer.post(
            "/api/events/evt_01/rubrics",
            json={
                "criteria": [
                    {
                        "label": f"Delivery {suffix}",
                        "description": "Working implementation",
                        "minimum_score": 0,
                        "maximum_score": 10,
                        "weight": 3,
                        "display_order": 1,
                    },
                    {
                        "label": f"Impact {suffix}",
                        "description": "Who benefits",
                        "minimum_score": 1,
                        "maximum_score": 5,
                        "weight": 2,
                        "display_order": 2,
                    },
                ]
            },
        )
        assert rubric_response.status_code == 201, rubric_response.text
        rubric = rubric_response.json()
        first_criterion, second_criterion = rubric["criteria"]

    async with httpx.AsyncClient(base_url=base_url) as judge_a:
        judge_a.cookies.set("session", "jdg_a_91bc")
        own_scores = await judge_a.get("/api/judge/scores")
        assert own_scores.status_code == 200
        assert own_scores.json()
        assert {item["judge_id"] for item in own_scores.json()} == {"jdg_01"}

        workspace = await judge_a.get("/api/judge/projects/prj_07/scorecard")
        assert workspace.status_code == 200
        assert workspace.json()["rubric"]["id"] == rubric["id"]
        assert workspace.json()["scorecard"] is None

        altered_actor = await judge_a.get(
            "/api/judge/scores", params={"judge_id": "jdg_02"}
        )
        assert altered_actor.status_code == 403

        unassigned_same_track = await judge_a.get(
            "/api/judge/projects/prj_02/scorecard"
        )
        assert unassigned_same_track.status_code == 403
        another_track = await judge_a.get(
            "/api/judge/projects/prj_01/scorecard"
        )
        assert another_track.status_code == 403

        guessed_peer = await judge_a.get(
            "/api/judge/scorecards/scr_jdg_02_prj_05"
        )
        assert guessed_peer.status_code == 404
        assert "Docs are thin." not in guessed_peer.text

        invalid_range = await judge_a.put(
            "/api/judge/projects/prj_07/scorecard",
            json={
                "rubric_id": rubric["id"],
                "comment": "private draft marker",
                "scores": [
                    {"criterion_id": first_criterion["id"], "score": 11}
                ],
            },
        )
        assert invalid_range.status_code == 400
        assert invalid_range.json()["error"]["code"] == "score_out_of_range"

        partial = await judge_a.put(
            "/api/judge/projects/prj_07/scorecard",
            json={
                "rubric_id": rubric["id"],
                "comment": "private draft marker",
                "scores": [
                    {"criterion_id": first_criterion["id"], "score": 8}
                ],
            },
        )
        assert partial.status_code == 200, partial.text
        draft = partial.json()
        assert draft["status"] == "draft"
        assert draft["judge_id"] == "jdg_01"
        assert draft["criteria"][1]["score"] is None

        incomplete = await judge_a.post(
            f"/api/judge/scorecards/{draft['id']}/submit"
        )
        assert incomplete.status_code == 409
        assert incomplete.json()["error"]["code"] == "scorecard_incomplete"

        complete = await judge_a.put(
            "/api/judge/projects/prj_07/scorecard",
            json={
                "rubric_id": rubric["id"],
                "comment": "private draft marker",
                "scores": [
                    {"criterion_id": first_criterion["id"], "score": 8},
                    {"criterion_id": second_criterion["id"], "score": 4},
                ],
            },
        )
        assert complete.status_code == 200, complete.text
        assert complete.json()["id"] == draft["id"]
        own_detail = await judge_a.get(f"/api/judge/scorecards/{draft['id']}")
        assert own_detail.status_code == 200
        assert own_detail.json()["comment"] == "private draft marker"

    async with httpx.AsyncClient(base_url=base_url) as judge_b:
        judge_b.cookies.set("session", "jdg_b_44de")
        peer_query = await judge_b.get(
            "/api/judge/scores",
            params={"judge_id": "jdg_01", "project_id": "prj_07"},
        )
        assert peer_query.status_code == 403
        peer_detail = await judge_b.get(f"/api/judge/scorecards/{draft['id']}")
        assert peer_detail.status_code == 404
        assert "private draft marker" not in peer_detail.text
        judge_b_scores = await judge_b.get("/api/judge/scores")
        assert judge_b_scores.status_code == 200
        assert {item["judge_id"] for item in judge_b_scores.json()} == {"jdg_02"}
        organizer_scores = await judge_b.get(
            "/api/organizer/events/evt_01/scorecards"
        )
        assert organizer_scores.status_code == 403
        assert "private draft marker" not in organizer_scores.text
        organizer_progress = await judge_b.get(
            "/api/organizer/events/evt_01/judging-progress"
        )
        assert organizer_progress.status_code == 403

    async with httpx.AsyncClient(base_url=base_url) as participant:
        participant.cookies.set("session", "prt_2e88")
        participant_list = await participant.get("/api/judge/scores")
        assert participant_list.status_code == 403
        participant_detail = await participant.get(
            f"/api/judge/scorecards/{draft['id']}"
        )
        assert participant_detail.status_code == 403
        participant_write = await participant.put(
            "/api/judge/projects/prj_07/scorecard",
            json={"rubric_id": rubric["id"], "scores": []},
        )
        assert participant_write.status_code == 403
        participant_organizer_scores = await participant.get(
            "/api/organizer/events/evt_01/scorecards"
        )
        assert participant_organizer_scores.status_code == 403

    async with httpx.AsyncClient(base_url=base_url) as judge_a:
        judge_a.cookies.set("session", "jdg_a_91bc")
        submitted = await judge_a.post(
            f"/api/judge/scorecards/{draft['id']}/submit"
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "submitted"
        assert submitted.json()["submitted_at"] is not None
        locked = await judge_a.put(
            "/api/judge/projects/prj_07/scorecard",
            json={
                "rubric_id": rubric["id"],
                "comment": "attempted rewrite",
                "scores": [
                    {"criterion_id": first_criterion["id"], "score": 7},
                    {"criterion_id": second_criterion["id"], "score": 3},
                ],
            },
        )
        assert locked.status_code == 409
        assert locked.json()["error"]["code"] == "scorecard_submitted"

    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        score_data = await organizer.get(
            "/api/organizer/events/evt_01/scorecards"
        )
        assert score_data.status_code == 200
        matching = [item for item in score_data.json() if item["id"] == draft["id"]]
        assert len(matching) == 1
        assert matching[0]["comment"] == "private draft marker"
        progress = await organizer.get(
            "/api/organizer/events/evt_01/judging-progress"
        )
        assert progress.status_code == 200
        assert any(
            item["judge_id"] == "jdg_01"
            and item["project_id"] == "prj_07"
            and item["status"] == "submitted"
            and item["rubric_version"] == rubric["version"]
            for item in progress.json()
        )
