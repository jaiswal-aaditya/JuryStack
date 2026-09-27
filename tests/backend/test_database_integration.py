"""Live PostgreSQL verification for the migrated and seeded database.

Run as pytest with JURYSTACK_TEST_DATABASE_URL set, or copy this file into the
API container and execute it directly. The direct mode uses DATABASE_URL.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections import Counter
from datetime import UTC
from pathlib import Path

from app.core.fixtures import load_fixture, stable_user_id
from app.core.seed import DEMO_TOKENS
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

EXPECTED_REVISION = "20260927_0006"


async def verify_seeded_database(database_url: str, fixture_path: Path) -> None:
    fixture = load_fixture(fixture_path)
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            scalar_expectations = {
                "SELECT count(*) FROM events": 1,
                "SELECT count(*) FROM tracks": 8,
                "SELECT count(*) FROM users WHERE role = 'judge'": 30,
                "SELECT count(*) FROM teams": 40,
                "SELECT count(*) FROM projects": 41,
                "SELECT count(*) FROM scorecards": 126,
                "SELECT count(*) FROM criterion_scores": 378,
                "SELECT count(*) FROM sessions": 4,
                "SELECT count(*) FROM scorecards WHERE comment = ''": 51,
            }
            for query, expected in scalar_expectations.items():
                assert await connection.scalar(text(query)) == expected

            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            assert revision == EXPECTED_REVISION

            invalid_foreign_keys = await connection.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM pg_constraint
                    WHERE contype = 'f' AND NOT convalidated
                    """
                )
            )
            foreign_key_count = await connection.scalar(
                text("SELECT count(*) FROM pg_constraint WHERE contype = 'f'")
            )
            assert invalid_foreign_keys == 0
            assert foreign_key_count >= 20

            savepoint = await connection.begin_nested()
            try:
                await connection.execute(
                    text(
                        """
                        INSERT INTO team_members (team_id, user_id)
                        VALUES ('tm_01', 'usr_missing_integrity_probe')
                        """
                    )
                )
            except IntegrityError:
                await savepoint.rollback()
            else:
                await savepoint.rollback()
                raise AssertionError("team_members accepted an orphan user reference")

            team_seven_projects = (
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM projects WHERE team_id = 'tm_07' "
                            "ORDER BY id"
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert team_seven_projects == ["prj_07", "prj_41"]

            project_rows = (
                await connection.execute(
                    text("SELECT id, submitted_at FROM projects ORDER BY id")
                )
            ).all()
            expected_times = {
                project.id: project.submitted_at for project in fixture.projects
            }
            assert {row.id for row in project_rows} == set(expected_times)
            for row in project_rows:
                assert isinstance(row.id, str)
                assert row.submitted_at.tzinfo is not None
                assert row.submitted_at.utcoffset() == UTC.utcoffset(row.submitted_at)
                assert row.submitted_at == expected_times[row.id]

            close_time = await connection.scalar(
                text("SELECT submissions_close FROM events WHERE id = :event_id"),
                {"event_id": fixture.event.id},
            )
            assert close_time == fixture.event.submissions_close
            assert close_time.utcoffset() == UTC.utcoffset(close_time)

            score_rows = (
                await connection.execute(
                    text(
                        """
                        SELECT s.judge_id, s.project_id, s.comment, rc.key, cs.score
                        FROM scorecards AS s
                        JOIN criterion_scores AS cs ON cs.scorecard_id = s.id
                        JOIN rubric_criteria AS rc ON rc.id = cs.criterion_id
                        ORDER BY s.judge_id, s.project_id, rc.key
                        """
                    )
                )
            ).all()
            actual_scores: dict[tuple[str, str], dict[str, object]] = {}
            for row in score_rows:
                record = actual_scores.setdefault(
                    (row.judge_id, row.project_id),
                    {"comment": row.comment, "criteria": {}},
                )
                assert record["comment"] == row.comment
                criteria = record["criteria"]
                assert isinstance(criteria, dict)
                criteria[row.key] = row.score

            expected_scores = {
                (score.judge, score.project): {
                    "comment": score.comment,
                    "criteria": score.criteria,
                }
                for score in fixture.scores
            }
            assert actual_scores == expected_scores

            review_counts = Counter(score.project for score in fixture.scores)
            assert Counter(review_counts.values()) == {2: 8, 3: 26, 4: 3, 5: 4}
            constant_scores = [
                value
                for score in fixture.scores
                if score.judge == "jdg_07"
                for value in score.criteria.values()
            ]
            assert constant_scores and set(constant_scores) == {4}

            participant_email = fixture.teams[0].members[0].casefold()
            expected_actor_ids = {
                "organizer": "usr_organizer",
                "judge_a": "jdg_01",
                "judge_b": "jdg_02",
                "participant": stable_user_id(participant_email),
            }
            session_rows = (
                await connection.execute(
                    text("SELECT id, user_id, token_hash FROM sessions ORDER BY id")
                )
            ).all()
            actual_sessions = {
                row.id.removeprefix("ses_"): (row.user_id, row.token_hash)
                for row in session_rows
            }
            assert actual_sessions == {
                role: (
                    expected_actor_ids[role],
                    hashlib.sha256(token.encode()).hexdigest(),
                )
                for role, token in DEMO_TOKENS.items()
            }
    finally:
        await engine.dispose()


def test_live_migration_and_seed_integrity() -> None:
    database_url = os.getenv("JURYSTACK_TEST_DATABASE_URL")
    if not database_url:
        import pytest

        pytest.skip("set JURYSTACK_TEST_DATABASE_URL to run the PostgreSQL test")
    fixture_path = Path(os.getenv("JURYSTACK_FIXTURES_PATH", "../../fixtures.json"))
    asyncio.run(verify_seeded_database(database_url, fixture_path))


if __name__ == "__main__":
    from app.core.config import settings

    asyncio.run(verify_seeded_database(settings.database_url, settings.fixtures_path))
    print("database integration checks passed")
