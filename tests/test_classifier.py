import json
from pathlib import Path

import pytest

from slopwatch.classifier import GENUINE_LABEL, SLOP_LABEL, classify

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize(
    "fixture, expected_label",
    [
        ("genuine_issue.json", GENUINE_LABEL),
        ("genuine_pr.json", GENUINE_LABEL),
        ("slop_pr_verbose.json", SLOP_LABEL),
        ("slop_issue_vague.json", SLOP_LABEL),
    ],
)
def test_classify_label(fixture, expected_label):
    verdict = classify(_load(fixture))
    assert verdict.label == expected_label


def test_slop_pr_scores_below_close_threshold():
    # verbose/templated but only a diff/description mismatch, not a total void
    # of content -- should land in the "ask first" band, not "close outright".
    verdict = classify(_load("slop_pr_verbose.json"))
    assert 50 <= verdict.score < 80


def test_slop_issue_scores_above_close_threshold():
    # boilerplate + vague language + templated headers + zero concrete
    # signals stacks high enough to close outright.
    verdict = classify(_load("slop_issue_vague.json"))
    assert verdict.score >= 80


def test_genuine_fixtures_score_low():
    for name in ("genuine_issue.json", "genuine_pr.json"):
        verdict = classify(_load(name))
        assert verdict.score < 50
