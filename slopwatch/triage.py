"""Maps a classifier Verdict to a triage action and drafts a first-response reply."""
from __future__ import annotations

import re
from dataclasses import dataclass

from slopwatch.classifier import SLOP_LABEL, Verdict

_POINTS_SUFFIX_RE = re.compile(r":\s*\+\d+$")

ACTION_NONE = "none"
ACTION_DRAFT_REPLY = "draft-reply"
ACTION_REQUEST_CLARIFICATION = "request-clarification"
ACTION_CLOSE = "close"

CLOSE_THRESHOLD = 80  # score >= this -> close outright instead of asking first


@dataclass
class Triage:
    action: str
    label: str
    reply: str


def decide(verdict: Verdict, kind: str) -> Triage:
    """`kind` is "issue" or "pr"."""
    if verdict.label == SLOP_LABEL:
        action = ACTION_CLOSE if verdict.score >= CLOSE_THRESHOLD else ACTION_REQUEST_CLARIFICATION
    else:
        action = ACTION_DRAFT_REPLY if kind == "issue" else ACTION_NONE

    reply = _draft_reply(action, verdict, kind)
    return Triage(action=action, label=verdict.label, reply=reply)


def _human_reasons(verdict: Verdict) -> str:
    """Reasons list without the internal scoring annotations (e.g. ': +20')."""
    return "; ".join(_POINTS_SUFFIX_RE.sub("", r) for r in verdict.reasons)


def _draft_reply(action: str, verdict: Verdict, kind: str):
    if action == ACTION_NONE:
        return None

    if action == ACTION_CLOSE:
        return (
            "Thanks for the submission. This doesn't include enough concrete detail "
            f"({_human_reasons(verdict)}) for a maintainer to act on, so I'm closing "
            "it as likely low-effort/automated. If this was a genuine contribution, "
            "please reopen with specific repro steps or a scoped description of the "
            "change and why it's needed."
        )

    if action == ACTION_REQUEST_CLARIFICATION:
        thing = "PR" if kind == "pr" else "issue"
        return (
            f"Thanks for the {thing}. Before we can review this, could you clarify what "
            "specific bug or behavior this addresses, the exact steps to reproduce it, "
            "and (for code changes) what test demonstrates the fix? A few automated "
            f"heuristics flagged this as possibly AI-generated ({_human_reasons(verdict)}) "
            "-- happy to be proven wrong with more detail."
        )

    if action == ACTION_DRAFT_REPLY:
        return (
            "Thanks for opening this issue -- it looks like a genuine report. A "
            "maintainer will take a look soon. In the meantime, if you can attach any "
            "logs, environment details, or a minimal reproduction, that'll speed up "
            "triage."
        )

    return None
