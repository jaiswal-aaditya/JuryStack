import csv
import io
from types import SimpleNamespace

import pytest

from app.results.service import (
    ProgressFilters,
    ResultsService,
    protect_csv_cell,
    raw_weighted_score,
)


def ns(**values):  # type: ignore[no-untyped-def]
    return SimpleNamespace(**values)


def test_weighted_score_handles_incomplete_criterion_data() -> None:
    card = ns(
        rubric=ns(
            criteria=[
                ns(id="quality", weight=3),
                ns(id="impact", weight=1),
            ]
        ),
        criterion_scores=[ns(criterion_id="quality", score=4)],
    )
    assert raw_weighted_score(card) == 4.0
    assert raw_weighted_score(None) is None


@pytest.mark.parametrize("dangerous", ["=1+1", "+SUM(A1:A2)", "-2", "@cmd"])
def test_csv_formula_injection_is_neutralized(dangerous: str) -> None:
    assert protect_csv_cell(dangerous) == f"'{dangerous}"
    assert protect_csv_cell("safe") == "safe"


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    def add(self, value) -> None:  # type: ignore[no-untyped-def]
        self.added.append(value)

    async def commit(self) -> None:
        self.committed = True


class FakeRepository:
    def __init__(self, event, projects, assignments, scorecards) -> None:  # type: ignore[no-untyped-def]
        self._event = event
        self._projects = projects
        self._assignments = assignments
        self._scorecards = scorecards

    async def event(self, event_id):  # type: ignore[no-untyped-def]
        return self._event

    async def projects(self, event_id):  # type: ignore[no-untyped-def]
        return self._projects

    async def assignments(self, event_id):  # type: ignore[no-untyped-def]
        return self._assignments

    async def scorecards(self, event_id):  # type: ignore[no-untyped-def]
        return self._scorecards


def sample_data():  # type: ignore[no-untyped-def]
    team = ns(id="tm_01", name="=Unsafe Team")
    track = ns(id="trk_01", name="Developer tools")
    project = ns(
        id="prj_01",
        event_id="evt_01",
        team_id=team.id,
        team=team,
        track_id=track.id,
        track=track,
        title="+Unsafe Project",
        status="submitted",
    )
    judge_a = ns(id="jdg_01", display_name="Judge A")
    judge_b = ns(id="jdg_02", display_name="Judge B")
    assignments = [
        ns(
            id="asg_1",
            judge_id=judge_a.id,
            judge=judge_a,
            project_id=project.id,
            project=project,
        ),
        ns(
            id="asg_2",
            judge_id=judge_b.id,
            judge=judge_b,
            project_id=project.id,
            project=project,
        ),
    ]
    rubric = ns(
        id="rub_1", version=1, criteria=[ns(id="c1", weight=2), ns(id="c2", weight=1)]
    )
    scorecards = [
        ns(
            id="scr_1",
            judge_id=judge_a.id,
            project_id=project.id,
            status="submitted",
            rubric_id=rubric.id,
            rubric=rubric,
            criterion_scores=[
                ns(criterion_id="c1", score=5),
                ns(criterion_id="c2", score=2),
            ],
            submitted_at=None,
        )
    ]
    return ns(id="evt_01"), [project], assignments, scorecards


@pytest.mark.asyncio
async def test_progress_counts_missing_and_submitted_and_coverage() -> None:
    event, projects, assignments, scorecards = sample_data()
    service = ResultsService(FakeSession())  # type: ignore[arg-type]
    service.repository = FakeRepository(event, projects, assignments, scorecards)  # type: ignore[assignment]
    result = await service.progress("evt_01", ProgressFilters(required_reviews=2))
    assert result.summary.total_assignments == 2
    assert result.summary.missing_scorecards == 1
    assert result.summary.submitted_scorecards == 1
    assert result.summary.completion_percentage == 50.0
    assert result.summary.insufficient_project_count == 1
    assert result.projects[0].assigned_reviews == 2
    assert result.projects[0].submitted_reviews == 1


@pytest.mark.asyncio
async def test_export_is_valid_csv_with_stable_fields_and_dangerous_cells() -> None:
    event, projects, assignments, scorecards = sample_data()
    session = FakeSession()
    service = ResultsService(session)  # type: ignore[arg-type]
    service.repository = FakeRepository(event, projects, assignments, scorecards)  # type: ignore[assignment]
    body = await service.csv_export(ns(id="usr_org"), "evt_01")
    rows = list(csv.DictReader(io.StringIO(body)))
    assert len(rows) == 2
    assert rows[0]["project_id"] == "prj_01"
    assert rows[0]["team_id"] == "tm_01"
    assert rows[0]["project_title"] == "'+Unsafe Project"
    assert rows[0]["team_name"] == "'=Unsafe Team"
    assert rows[0]["raw_weighted_score"] == "4.0"
    assert rows[1]["scorecard_status"] == "missing"
    assert session.committed
    assert session.added[0].action == "results.exported"
