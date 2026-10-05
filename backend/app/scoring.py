"""Scoring rules from SPEC section 3.3. Pure functions: no AI, no database.

This module is the source of truth. src/lib/scoring.ts mirrors it so the
screen can update at once; both run shared/scoring_cases.json in their tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Answer = Literal["Yes", "Partly", "No", "Dont_know"]
Verdict = Literal["fix", "go", "ready", "not_assessed"]
Band = Literal["weak", "partial", "strong", "none"]

POINTS: dict[str, int] = {"Yes": 5, "Partly": 3, "No": 1, "Dont_know": 1}
DIMENSION_IDS: tuple[int, ...] = tuple(range(1, 9))
TOTAL_QUESTIONS = 40
NO_CAP = 3.0
FIX_MAX = 2.4
GO_MAX = 3.4

VERDICT_LABELS: dict[str, str] = {
    "fix": "Fix before next stage",
    "go": "Go with actions",
    "ready": "Ready",
    "not_assessed": "Not assessed",
}
# Portfolio sort order: fix -> go -> ready -> not assessed.
VERDICT_ORDER: dict[str, int] = {"fix": 0, "go": 1, "ready": 2, "not_assessed": 3}


@dataclass(frozen=True)
class DimensionScore:
    id: int
    score: float | None
    raw: float | None
    capped: bool
    has_no: bool
    answered: int
    band: Band


@dataclass(frozen=True)
class ScoreResult:
    dimensions: list[DimensionScore]
    lowest: float | None
    weakest: list[int]
    verdict: Verdict
    answered: int
    coverage: float
    partial: bool
    dimension_scores: dict[int, float | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def round1(value: float) -> float:
    """Round to 1 decimal, halves away from zero (same as the client)."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def band(score: float | None) -> Band:
    if score is None:
        return "none"
    if score <= FIX_MAX:
        return "weak"
    if score <= GO_MAX:
        return "partial"
    return "strong"


def score_dimension(answers: Iterable[str | None], dimension_id: int = 0) -> DimensionScore:
    """Average the answered questions; any No caps the score at 3.0."""
    given = [a for a in answers if a in POINTS]
    if not given:
        return DimensionScore(dimension_id, None, None, False, False, 0, "none")
    raw = round1(sum(POINTS[a] for a in given) / len(given))
    has_no = "No" in given
    capped = has_no and raw > NO_CAP
    score = NO_CAP if capped else raw
    return DimensionScore(dimension_id, score, raw, capped, has_no, len(given), band(score))


def summarise(dimension_scores: Mapping[int, float | None], answered: int) -> dict:
    """Lowest, weakest link and verdict from the dimension scores."""
    scored = {int(k): v for k, v in dimension_scores.items() if v is not None}
    if not scored:
        return {
            "lowest": None,
            "weakest": [],
            "verdict": "not_assessed",
            "partial": answered < TOTAL_QUESTIONS,
        }
    lowest = min(scored.values())
    weakest = sorted(k for k, v in scored.items() if v == lowest)
    if lowest <= FIX_MAX:
        verdict: Verdict = "fix"
    elif lowest <= GO_MAX:
        verdict = "go"
    else:
        verdict = "ready"
    return {
        "lowest": lowest,
        "weakest": weakest,
        "verdict": verdict,
        "partial": answered < TOTAL_QUESTIONS,
    }


def dimension_of(question_id: str) -> int | None:
    """'5.1' -> 5. Anything that is not a known dimension returns None."""
    head, _, tail = str(question_id).partition(".")
    if not head.isdigit() or not tail.isdigit():
        return None
    dim = int(head)
    return dim if dim in DIMENSION_IDS else None


def score_project(answers: Mapping[str, str | None]) -> ScoreResult:
    """answers maps question ID ('5.1') to an answer or None (blank)."""
    by_dim: dict[int, list[str | None]] = {d: [] for d in DIMENSION_IDS}
    for qid, answer in answers.items():
        dim = dimension_of(qid)
        if dim is not None:
            by_dim[dim].append(answer)
    dims = [score_dimension(by_dim[d], d) for d in DIMENSION_IDS]
    answered = sum(d.answered for d in dims)
    scores = {d.id: d.score for d in dims}
    summary = summarise(scores, answered)
    return ScoreResult(
        dimensions=dims,
        lowest=summary["lowest"],
        weakest=summary["weakest"],
        verdict=summary["verdict"],
        answered=answered,
        coverage=answered / TOTAL_QUESTIONS,
        partial=summary["partial"],
        dimension_scores=scores,
    )
