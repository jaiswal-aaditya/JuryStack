"""Deterministic cross-judge normalization.

This is the only module that performs score weighting, calibration, aggregation,
or ranking. Transport and persistence layers only adapt data to/from these
immutable inputs and outputs.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import fmean, median, pvariance

ROUND_DIGITS = 6
ZERO_TOLERANCE = 1e-12


@dataclass(frozen=True)
class CriterionValue:
    criterion_id: str
    score: int | None
    minimum_score: int
    maximum_score: int
    weight: int


@dataclass(frozen=True)
class ReviewInput:
    review_id: str
    judge_id: str
    project_id: str
    status: str
    criteria: tuple[CriterionValue, ...]
    rubric_id: str = "default"


@dataclass(frozen=True)
class ScoredReview:
    review_id: str
    judge_id: str
    project_id: str
    eligible: bool
    exclusion_reason: str | None
    raw_weighted_total: float | None
    raw_percentage: float | None
    rubric_id: str


@dataclass(frozen=True)
class JudgeCalibration:
    judge_id: str
    eligible_review_count: int
    overlap_count: int
    raw_variance: float
    bias: float
    fallback_used: str


@dataclass(frozen=True)
class ReviewContribution:
    review_id: str
    judge_id: str
    project_id: str
    raw_weighted_total: float
    raw_percentage: float
    judge_bias: float
    normalized_contribution: float
    fallback_used: str


@dataclass(frozen=True)
class ProjectRanking:
    project_id: str
    eligible: bool
    eligibility_reason: str | None
    review_count: int
    excluded_review_count: int
    raw_total: float | None
    final_value: float | None
    raw_rank: int | None
    rank: int | None
    rank_movement: int | None
    fallbacks_used: tuple[str, ...]
    contributions: tuple[ReviewContribution, ...]


@dataclass(frozen=True)
class NormalizationResult:
    projects: tuple[ProjectRanking, ...]
    judges: tuple[JudgeCalibration, ...]
    rubric_id: str | None


def score_review(review: ReviewInput) -> ScoredReview:
    if review.status != "submitted":
        return _excluded(review, "not_submitted")
    if not review.criteria or any(item.score is None for item in review.criteria):
        return _excluded(review, "missing_criterion_score")
    if any(
        item.weight <= 0
        or item.minimum_score >= item.maximum_score
        or item.score is None
        or item.score < item.minimum_score
        or item.score > item.maximum_score
        for item in review.criteria
    ):
        return _excluded(review, "invalid_score_or_rubric")

    raw_total = float(
        sum(
            item.weight * item.score
            for item in review.criteria
            if item.score is not None
        )
    )
    minimum_total = sum(item.weight * item.minimum_score for item in review.criteria)
    available_range = sum(
        item.weight * (item.maximum_score - item.minimum_score)
        for item in review.criteria
    )
    percentage = 100.0 * (raw_total - minimum_total) / available_range
    return ScoredReview(
        review_id=review.review_id,
        judge_id=review.judge_id,
        project_id=review.project_id,
        eligible=True,
        exclusion_reason=None,
        raw_weighted_total=_round(raw_total),
        raw_percentage=_round(percentage),
        rubric_id=review.rubric_id,
    )


def normalize_rankings(
    reviews: list[ReviewInput],
    project_ids: list[str],
    *,
    minimum_reviews: int = 2,
    minimum_overlap: int = 2,
) -> NormalizationResult:
    if minimum_reviews < 1 or minimum_overlap < 1:
        raise ValueError("minimum review and overlap counts must be positive")

    scored = [score_review(review) for review in reviews]
    rubric_counts: dict[str, int] = defaultdict(int)
    for review in scored:
        if review.eligible:
            rubric_counts[review.rubric_id] += 1
    selected_rubric_id = (
        min(
            rubric_counts,
            key=lambda rubric_id: (-rubric_counts[rubric_id], rubric_id),
        )
        if rubric_counts
        else None
    )
    eligible = [
        review
        for review in scored
        if review.eligible and review.rubric_id == selected_rubric_id
    ]
    by_project: dict[str, list[ScoredReview]] = defaultdict(list)
    by_judge: dict[str, list[ScoredReview]] = defaultdict(list)
    excluded_by_project: dict[str, int] = defaultdict(int)
    for review in scored:
        if review.eligible and review.rubric_id == selected_rubric_id:
            by_project[review.project_id].append(review)
            by_judge[review.judge_id].append(review)
        else:
            excluded_by_project[review.project_id] += 1

    calibrations: dict[str, JudgeCalibration] = {}
    for judge_id, judge_reviews in sorted(by_judge.items()):
        differences: list[float] = []
        raw_values = [required(review.raw_percentage) for review in judge_reviews]
        for review in judge_reviews:
            peers = [
                required(peer.raw_percentage)
                for peer in by_project[review.project_id]
                if peer.judge_id != judge_id
            ]
            if peers:
                differences.append(required(review.raw_percentage) - fmean(peers))
        variance = pvariance(raw_values) if len(raw_values) > 1 else 0.0
        if len(judge_reviews) == 1:
            bias = 0.0
            fallback = "single_review_raw"
        elif len(differences) < minimum_overlap:
            bias = 0.0
            fallback = "insufficient_overlap_raw"
        else:
            bias = median(differences)
            fallback = (
                "zero_variance_paired_median" if variance <= ZERO_TOLERANCE else "none"
            )
        calibrations[judge_id] = JudgeCalibration(
            judge_id=judge_id,
            eligible_review_count=len(judge_reviews),
            overlap_count=len(differences),
            raw_variance=_round(variance),
            bias=_round(bias),
            fallback_used=fallback,
        )

    contributions_by_project: dict[str, list[ReviewContribution]] = defaultdict(list)
    for review in eligible:
        calibration = calibrations[review.judge_id]
        contribution = min(
            100.0,
            max(0.0, required(review.raw_percentage) - calibration.bias),
        )
        contributions_by_project[review.project_id].append(
            ReviewContribution(
                review_id=review.review_id,
                judge_id=review.judge_id,
                project_id=review.project_id,
                raw_weighted_total=required(review.raw_weighted_total),
                raw_percentage=required(review.raw_percentage),
                judge_bias=calibration.bias,
                normalized_contribution=_round(contribution),
                fallback_used=calibration.fallback_used,
            )
        )

    aggregates: dict[str, tuple[float, float]] = {}
    for project_id, items in contributions_by_project.items():
        if len(items) >= minimum_reviews:
            aggregates[project_id] = (
                _round(fmean(item.raw_percentage for item in items)),
                _round(fmean(item.normalized_contribution for item in items)),
            )
    raw_ranks = competition_ranks({key: value[0] for key, value in aggregates.items()})
    final_ranks = competition_ranks(
        {key: value[1] for key, value in aggregates.items()}
    )

    projects: list[ProjectRanking] = []
    for project_id in sorted(set(project_ids)):
        items = tuple(
            sorted(
                contributions_by_project.get(project_id, []),
                key=lambda item: (item.judge_id, item.review_id),
            )
        )
        if project_id not in aggregates:
            projects.append(
                ProjectRanking(
                    project_id=project_id,
                    eligible=False,
                    eligibility_reason=f"fewer_than_{minimum_reviews}_complete_reviews",
                    review_count=len(items),
                    excluded_review_count=excluded_by_project[project_id],
                    raw_total=None,
                    final_value=None,
                    raw_rank=None,
                    rank=None,
                    rank_movement=None,
                    fallbacks_used=tuple(
                        sorted({item.fallback_used for item in items})
                    ),
                    contributions=items,
                )
            )
            continue
        raw_value, final_value = aggregates[project_id]
        projects.append(
            ProjectRanking(
                project_id=project_id,
                eligible=True,
                eligibility_reason=None,
                review_count=len(items),
                excluded_review_count=excluded_by_project[project_id],
                raw_total=raw_value,
                final_value=final_value,
                raw_rank=raw_ranks[project_id],
                rank=final_ranks[project_id],
                rank_movement=raw_ranks[project_id] - final_ranks[project_id],
                fallbacks_used=tuple(sorted({item.fallback_used for item in items})),
                contributions=items,
            )
        )
    projects.sort(
        key=lambda item: (
            item.rank is None,
            item.rank if item.rank is not None else 10**9,
            item.project_id,
        )
    )
    return NormalizationResult(
        projects=tuple(projects),
        judges=tuple(calibrations[key] for key in sorted(calibrations)),
        rubric_id=selected_rubric_id,
    )


def competition_ranks(values: dict[str, float]) -> dict[str, int]:
    ordered_values = sorted(values.values(), reverse=True)
    return {
        key: 1 + sum(other > value + ZERO_TOLERANCE for other in ordered_values)
        for key, value in values.items()
    }


def required(value: float | None) -> float:
    if value is None:
        raise ValueError("eligible reviews must have calculated values")
    return value


def _excluded(review: ReviewInput, reason: str) -> ScoredReview:
    return ScoredReview(
        review_id=review.review_id,
        judge_id=review.judge_id,
        project_id=review.project_id,
        eligible=False,
        exclusion_reason=reason,
        raw_weighted_total=None,
        raw_percentage=None,
        rubric_id=review.rubric_id,
    )


def _round(value: float) -> float:
    return round(value, ROUND_DIGITS)
