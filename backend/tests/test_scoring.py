"""Runs shared/scoring_cases.json, the same file Vitest runs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.scoring import band, round1, score_dimension, score_project, summarise

CASES = json.loads(
    (Path(__file__).resolve().parents[2] / "shared" / "scoring_cases.json").read_text()
)


@pytest.mark.parametrize("case", CASES["dimension_cases"], ids=lambda c: c["name"])
def test_dimension(case: dict) -> None:
    d = score_dimension(case["answers"])
    assert d.raw == case["raw"]
    assert d.score == case["score"]
    assert d.capped is case["capped"]
    assert d.has_no is case["has_no"]
    assert d.answered == case["answered"]


@pytest.mark.parametrize("case", CASES["summary_cases"], ids=lambda c: c["name"])
def test_summary(case: dict) -> None:
    scores = {int(k): v for k, v in case["dimension_scores"].items()}
    s = summarise(scores, case["answered"])
    assert s["lowest"] == case["lowest"]
    assert s["weakest"] == case["weakest"]
    assert s["verdict"] == case["verdict"]
    assert s["partial"] is case["partial"]


@pytest.mark.parametrize("case", CASES["project_cases"], ids=lambda c: c["name"])
def test_project(case: dict) -> None:
    r = score_project(case["answers"])
    assert r.dimension_scores == {int(k): v for k, v in case["dimension_scores"].items()}
    assert r.lowest == case["lowest"]
    assert r.weakest == case["weakest"]
    assert r.verdict == case["verdict"]
    assert r.answered == case["answered"]
    assert r.coverage == pytest.approx(case["coverage"])
    assert r.partial is case["partial"]


def test_bands() -> None:
    assert [band(s) for s in (None, 1.0, 2.4, 2.5, 3.4, 3.5, 5.0)] == [
        "none",
        "weak",
        "weak",
        "partial",
        "partial",
        "strong",
        "strong",
    ]


def test_round_half_up() -> None:
    assert round1(2.25) == 2.3
    assert round1(2.35) == 2.4
    assert round1(7 / 3) == 2.3
