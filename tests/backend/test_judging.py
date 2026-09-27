from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from app.core.errors import Conflict, InvalidRequest
from app.core.models import JudgeInvitation, Rubric, RubricCriterion
from app.judging.schemas import (
    JudgeInvitationAccept,
    RubricCreate,
    ScorecardDraftInput,
)
from app.judging.service import JudgingService, plan_balanced_assignments
from pydantic import ValidationError


def test_rubric_rejects_invalid_weights_and_score_ranges() -> None:
    base = {
        "label": "Impact",
        "description": "Who benefits",
        "minimum_score": 1,
        "maximum_score": 5,
        "weight": 2,
        "display_order": 1,
    }
    with pytest.raises(ValidationError):
        RubricCreate.model_validate({"criteria": [{**base, "weight": 0}]})
    with pytest.raises(ValidationError):
        RubricCreate.model_validate(
            {"criteria": [{**base, "minimum_score": 5, "maximum_score": 5}]}
        )
    with pytest.raises(ValidationError):
        RubricCreate.model_validate(
            {"criteria": [base, {**base, "display_order": 2}]}
        )
    with pytest.raises(ValidationError):
        RubricCreate.model_validate({"criteria": [{**base, "label": "   "}]})


def test_new_judge_display_name_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        JudgeInvitationAccept.model_validate(
            {"display_name": "   ", "password": "long-local-password"}
        )


def test_expired_and_used_judge_invitations_are_rejected() -> None:
    expired = JudgeInvitation(
        id="jiv_expired",
        event_id="evt_01",
        email="judge@example.org",
        token_hash="hash",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        accepted_by_user_id=None,
    )
    with pytest.raises(Conflict) as expired_error:
        JudgingService._require_available_invitation(expired)
    assert expired_error.value.code == "invitation_expired"

    used = JudgeInvitation(
        id="jiv_used",
        event_id="evt_01",
        email="judge@example.org",
        token_hash="hash2",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        accepted_by_user_id="usr_judge",
    )
    with pytest.raises(Conflict) as used_error:
        JudgingService._require_available_invitation(used)
    assert used_error.value.code == "invitation_used"


def test_balancer_respects_tracks_avoids_duplicates_and_equalizes_load() -> None:
    planned = plan_balanced_assignments(
        projects=[("p1", "t1"), ("p2", "t1"), ("p3", "t2")],
        judge_tracks={"j1": {"t1", "t2"}, "j2": {"t1"}, "j3": {"t2"}},
        existing={("j1", "p1")},
        reviews_per_project=2,
    )
    combined = set(planned) | {("j1", "p1")}
    assert len(combined) == len(planned) + 1
    project_tracks = {"p1": "t1", "p2": "t1", "p3": "t2"}
    judge_tracks = {"j1": {"t1", "t2"}, "j2": {"t1"}, "j3": {"t2"}}
    assert all(
        project_tracks[project] in judge_tracks[judge]
        for judge, project in combined
    )
    counts = {judge: 0 for judge in ("j1", "j2", "j3")}
    for judge, _ in combined:
        counts[judge] += 1
    assert counts == {"j1": 3, "j2": 2, "j3": 1}

    evenly_planned = plan_balanced_assignments(
        projects=[("p1", "t1"), ("p2", "t1"), ("p3", "t1")],
        judge_tracks={"j1": {"t1"}, "j2": {"t1"}, "j3": {"t1"}},
        existing=set(),
        reviews_per_project=2,
    )
    even_counts = Counter(judge for judge, _ in evenly_planned)
    assert even_counts == {"j1": 2, "j2": 2, "j3": 2}


def test_balancer_fails_atomically_when_a_track_has_too_few_judges() -> None:
    with pytest.raises(Conflict) as error:
        plan_balanced_assignments(
            projects=[("p1", "t1")],
            judge_tracks={"j1": {"t1"}},
            existing=set(),
            reviews_per_project=2,
        )
    assert error.value.code == "insufficient_eligible_judges"


def test_scorecard_scores_must_match_criterion_ranges_and_identity() -> None:
    rubric = Rubric(id="rub_test", event_id="evt_test", version=1, is_active=True)
    rubric.criteria = [
        RubricCriterion(
            id="crit_impact",
            rubric_id=rubric.id,
            key="impact",
            label="Impact",
            description="",
            weight=2,
            minimum_score=0,
            maximum_score=10,
            position=1,
        )
    ]
    valid = ScorecardDraftInput.model_validate(
        {
            "rubric_id": rubric.id,
            "scores": [{"criterion_id": "crit_impact", "score": 10}],
        }
    )
    assert JudgingService._validated_scores(rubric, valid) == {"crit_impact": 10}

    out_of_range = ScorecardDraftInput.model_validate(
        {
            "rubric_id": rubric.id,
            "scores": [{"criterion_id": "crit_impact", "score": 11}],
        }
    )
    with pytest.raises(InvalidRequest) as range_error:
        JudgingService._validated_scores(rubric, out_of_range)
    assert range_error.value.code == "score_out_of_range"

    wrong_criterion = ScorecardDraftInput.model_validate(
        {
            "rubric_id": rubric.id,
            "scores": [{"criterion_id": "crit_peer", "score": 5}],
        }
    )
    with pytest.raises(InvalidRequest) as identity_error:
        JudgingService._validated_scores(rubric, wrong_criterion)
    assert identity_error.value.code == "criterion_mismatch"

    with pytest.raises(ValidationError):
        ScorecardDraftInput.model_validate(
            {
                "rubric_id": rubric.id,
                "scores": [
                    {"criterion_id": "crit_impact", "score": 3},
                    {"criterion_id": "crit_impact", "score": 4},
                ],
            }
        )
