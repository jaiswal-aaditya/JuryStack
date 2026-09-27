import csv
import io
import os

import httpx
import pytest

BASE_URL = os.getenv("JURYSTACK_TEST_BASE_URL")


def require_live() -> str:
    if not BASE_URL:
        pytest.skip("set JURYSTACK_TEST_BASE_URL to run live results tests")
    return BASE_URL


@pytest.mark.asyncio
async def test_results_export_authorization_and_csv_contract() -> None:
    base_url = require_live()
    async with httpx.AsyncClient(base_url=base_url) as anonymous:
        assert (await anonymous.get("/api/organizer/results.csv")).status_code == 401
    for token in ("prt_2e88", "jdg_a_91bc"):
        async with httpx.AsyncClient(base_url=base_url) as client:
            client.cookies.set("session", token)
            assert (await client.get("/api/organizer/results.csv")).status_code == 403
            assert (await client.get("/api/organizer/audit-events")).status_code == 403
            assert (
                await client.post("/api/organizer/events/evt_01/results/publish")
            ).status_code == 403
    async with httpx.AsyncClient(base_url=base_url) as organizer:
        organizer.cookies.set("session", "org_7f2a")
        response = await organizer.get("/api/organizer/results.csv")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert rows
        assert {"project_id", "team_id", "track_id", "raw_weighted_score"} <= rows[
            0
        ].keys()
        progress = await organizer.get("/api/organizer/events/evt_01/progress")
        assert progress.status_code == 200
        assert progress.json()["summary"]["total_assignments"] > 0
        publication = await organizer.post(
            "/api/organizer/events/evt_01/results/publish"
        )
        assert publication.status_code == 200
        assert publication.json()["event_id"] == "evt_01"
        audit = await organizer.get(
            "/api/organizer/audit-events", params={"action": "results."}
        )
        assert audit.status_code == 200
        assert {item["action"] for item in audit.json()} >= {
            "results.exported",
            "results.published",
        }
