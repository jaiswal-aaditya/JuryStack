from pathlib import Path

from app.core.fixtures import load_fixture
from app.core.seed import DEMO_TOKENS, build_seed_rows, token_hash

ROOT = Path(__file__).parents[2]


def test_fixture_seed_rows_are_complete_and_deterministic() -> None:
    fixture = load_fixture(ROOT / "fixtures.json")

    first = build_seed_rows(fixture)
    second = build_seed_rows(fixture)

    assert first == second
    assert len(first["tracks"]) == 8
    assert len(first["teams"]) == 40
    assert len(first["projects"]) == 41
    assert len(first["scorecards"]) == 126
    assert len(first["criterion_scores"]) == 378
    assert len(first["sessions"]) == 4


def test_seeded_checker_actors_have_consistent_fixture_mappings() -> None:
    fixture = load_fixture(ROOT / "fixtures.json")
    rows = build_seed_rows(fixture)
    sessions = {row["id"]: row for row in rows["sessions"]}

    assert sessions["ses_judge_a"]["user_id"] == "jdg_01"
    assert sessions["ses_judge_b"]["user_id"] == "jdg_02"
    participant_email = fixture.teams[0].members[0].casefold()
    participant = next(
        user for user in rows["users"] if user["email"] == participant_email
    )
    assert sessions["ses_participant"]["user_id"] == participant["id"]
    assert sessions["ses_organizer"]["user_id"] == "usr_organizer"
    assert {
        row["token_hash"] for row in sessions.values()
    } == {token_hash(token) for token in DEMO_TOKENS.values()}


def test_fixture_timestamps_parse_as_aware_utc() -> None:
    fixture = load_fixture(ROOT / "fixtures.json")

    timestamps = [
        fixture.event.submissions_close,
        *(project.submitted_at for project in fixture.projects),
    ]
    assert all(timestamp.tzinfo is not None for timestamp in timestamps)
    assert all(timestamp.utcoffset().total_seconds() == 0 for timestamp in timestamps)


def test_fixture_seed_preserves_two_projects_for_team_seven() -> None:
    rows = build_seed_rows(load_fixture(ROOT / "fixtures.json"))

    team_projects = [
        project["id"] for project in rows["projects"] if project["team_id"] == "tm_07"
    ]

    assert team_projects == ["prj_07", "prj_41"]


def test_seed_rows_have_unique_logical_keys() -> None:
    rows = build_seed_rows(load_fixture(ROOT / "fixtures.json"))

    assert len({row["id"] for row in rows["users"]}) == len(rows["users"])
    assert len({row["id"] for row in rows["projects"]}) == len(rows["projects"])
    assert len({row["id"] for row in rows["scorecards"]}) == len(rows["scorecards"])
    assert len(
        {(row["scorecard_id"], row["criterion_id"]) for row in rows["criterion_scores"]}
    ) == len(rows["criterion_scores"])
