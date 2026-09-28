import json
from pathlib import Path

import pytest

from app.results.normalization import (
    CriterionValue,
    ReviewInput,
    normalize_rankings,
)

FIXTURE_PATH = Path(__file__).parents[2] / "fixtures.json"


def fixture_reviews() -> tuple[list[ReviewInput], list[str]]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    reviews = [
        ReviewInput(
            review_id=f"scr_{item['judge']}_{item['project']}",
            judge_id=item["judge"],
            project_id=item["project"],
            status="submitted",
            criteria=tuple(
                CriterionValue(
                    criterion_id=key,
                    score=item["criteria"][key],
                    minimum_score=1,
                    maximum_score=5,
                    weight=1,
                )
                for key in ("functionality", "quality", "innovation")
            ),
        )
        for item in fixture["scores"]
    ]
    return reviews, [item["id"] for item in fixture["projects"]]


def test_fixture_zero_variance_judge_uses_paired_median_without_division() -> None:
    reviews, project_ids = fixture_reviews()
    result = normalize_rankings(reviews, project_ids)
    judge = next(item for item in result.judges if item.judge_id == "jdg_07")
    assert judge.eligible_review_count == 3
    assert judge.overlap_count == 3
    assert judge.raw_variance == 0
    assert judge.bias == pytest.approx(16.666667)
    assert judge.fallback_used == "zero_variance_paired_median"
    contributions = [
        contribution
        for project in result.projects
        for contribution in project.contributions
        if contribution.judge_id == "jdg_07"
    ]
    assert len(contributions) == 3
    assert {item.raw_percentage for item in contributions} == {75.0}
    assert all(
        item.normalized_contribution == pytest.approx(58.333333)
        for item in contributions
    )


def test_fixture_one_review_fallback_and_unequal_review_counts_are_explicit() -> None:
    reviews, project_ids = fixture_reviews()
    result = normalize_rankings(reviews, project_ids)
    judges = {item.judge_id: item for item in result.judges}
    assert judges["jdg_01"].fallback_used == "single_review_raw"
    assert judges["jdg_23"].fallback_used == "single_review_raw"
    projects = {item.project_id: item for item in result.projects}
    assert projects["prj_07"].review_count == 5
    assert projects["prj_01"].review_count == 3
    assert projects["prj_09"].review_count == 3
    assert projects["prj_09"].final_value == pytest.approx(
        sum(item.normalized_contribution for item in projects["prj_09"].contributions)
        / 3
    )
    assert all(project.eligible for project in result.projects)
    assert result.projects[0].project_id == "prj_11"
    assert result.projects[0].rank == 1


def test_missing_draft_and_incomplete_reviews_are_excluded_not_invented() -> None:
    complete = lambda review_id, judge_id, score: ReviewInput(  # noqa: E731
        review_id=review_id,
        judge_id=judge_id,
        project_id="p1",
        status="submitted",
        criteria=(CriterionValue("c1", score, 1, 5, 1),),
    )
    reviews = [
        complete("r1", "j1", 5),
        complete("r2", "j2", 3),
        ReviewInput(
            "r3", "j3", "p1", "submitted", (CriterionValue("c1", None, 1, 5, 1),)
        ),
        ReviewInput("r4", "j4", "p1", "draft", (CriterionValue("c1", 4, 1, 5, 1),)),
    ]
    result = normalize_rankings(reviews, ["p1", "p2"])
    projects = {item.project_id: item for item in result.projects}
    assert projects["p1"].eligible
    assert projects["p1"].review_count == 2
    assert projects["p1"].excluded_review_count == 2
    assert len(projects["p1"].contributions) == 2
    assert not projects["p2"].eligible
    assert projects["p2"].review_count == 0
    assert projects["p2"].final_value is None


def test_insufficient_overlap_keeps_raw_value_and_flags_fallback() -> None:
    reviews = [
        ReviewInput("r1", "j1", "p1", "submitted", (CriterionValue("c", 5, 1, 5, 1),)),
        ReviewInput("r2", "j2", "p1", "submitted", (CriterionValue("c", 3, 1, 5, 1),)),
        ReviewInput("r3", "j1", "p2", "submitted", (CriterionValue("c", 4, 1, 5, 1),)),
    ]
    result = normalize_rankings(reviews, ["p1", "p2"])
    judge = next(item for item in result.judges if item.judge_id == "j1")
    assert judge.overlap_count == 1
    assert judge.bias == 0
    assert judge.fallback_used == "insufficient_overlap_raw"
    p1 = next(item for item in result.projects if item.project_id == "p1")
    j1 = next(item for item in p1.contributions if item.judge_id == "j1")
    assert j1.normalized_contribution == j1.raw_percentage
