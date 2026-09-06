import json
from pathlib import Path

from slopwatch.classifier import classify
from slopwatch.triage import (
    ACTION_CLOSE,
    ACTION_DRAFT_REPLY,
    ACTION_NONE,
    ACTION_REQUEST_CLARIFICATION,
    decide,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def test_genuine_pr_has_no_action_or_reply():
    verdict = classify(_load("genuine_pr.json"))
    triage = decide(verdict, "pr")
    assert triage.action == ACTION_NONE
    assert triage.reply is None


def test_genuine_issue_gets_drafted_reply():
    verdict = classify(_load("genuine_issue.json"))
    triage = decide(verdict, "issue")
    assert triage.action == ACTION_DRAFT_REPLY
    assert triage.reply is not None


def test_slop_pr_requests_clarification():
    verdict = classify(_load("slop_pr_verbose.json"))
    triage = decide(verdict, "pr")
    assert triage.action == ACTION_REQUEST_CLARIFICATION
    assert triage.reply is not None


def test_slop_issue_is_closed():
    verdict = classify(_load("slop_issue_vague.json"))
    triage = decide(verdict, "issue")
    assert triage.action == ACTION_CLOSE
    assert triage.reply is not None
