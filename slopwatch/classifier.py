"""Deterministic heuristic scorer for AI-slop vs. genuine-effort classification.

The heuristic is the demoable core of the idea: boilerplate-phrase detection,
vague-language density, missing-concrete-signal detection, templated section
headers, and diff-vs-description mismatch/padding. It runs with zero API
keys. If ANTHROPIC_API_KEY is set, classify_with_claude() offers the same
Verdict shape via a Claude call, as an upgrade path only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

SLOP_LABEL = "likely-ai-slop"
GENUINE_LABEL = "human-effort"

SLOP_THRESHOLD = 50  # score >= this -> likely-ai-slop

BOILERPLATE_PHRASES = [
    "as an ai language model",
    "i hope this helps",
    "please let me know if you need any further",
    "please let me know if you have any questions",
    "this pull request addresses",
    "this pr addresses",
    "this change ensures",
    "i have carefully reviewed",
    "i've carefully reviewed",
    "thank you for the opportunity",
    "this commit introduces",
    "to improve code quality and maintainability",
    "ensures the code follows best practices",
    "i've made the following changes",
    "certainly! here is",
    "sure, here's",
    "i understand you're looking for",
    "i understand you are experiencing",
    "i apologize for any confusion",
    "let me know if you need any changes",
    "this should resolve the issue",
]

VAGUE_WORDS = [
    "various", "certain", "several", "things", "stuff", "issue", "issues",
    "problem", "problems", "improve", "enhance", "optimize", "robustness",
    "efficiency", "leverage", "ensure", "seamless", "functionality",
]

TEMPLATE_HEADERS = ["## summary", "## changes", "## motivation", "## testing", "## description"]

CODE_FILE_EXTENSION_RE = r"[\w./-]+\.(?:py|js|ts|go|rb|java|rs|c|cpp|md)\b"


@dataclass
class Verdict:
    score: float
    label: str
    reasons: list = field(default_factory=list)

    @property
    def is_slop(self) -> bool:
        return self.label == SLOP_LABEL


def _count_matches(text: str, phrases: list) -> int:
    lowered = text.lower()
    return sum(1 for p in phrases if p in lowered)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _boilerplate_points(body: str, reasons: list) -> float:
    hits = _count_matches(body, BOILERPLATE_PHRASES)
    if hits:
        points = min(hits * 12, 40)
        reasons.append(f"boilerplate AI phrasing detected ({hits} match{'es' if hits != 1 else ''}): +{points:.0f}")
        return points
    return 0.0


def _vague_language_points(body: str, reasons: list) -> float:
    words = _word_count(body)
    if words == 0:
        return 0.0
    vague_hits = _count_matches(body, VAGUE_WORDS)
    ratio = vague_hits / words
    if ratio > 0.03:
        points = min(ratio * 300, 25)
        reasons.append(f"high density of vague/generic language ({vague_hits} hits / {words} words): +{points:.0f}")
        return points
    return 0.0


def _specificity_deficit_points(body: str, reasons: list) -> float:
    has_code_block = "```" in body
    has_traceback = bool(re.search(r"traceback|stack trace|error:|exception", body, re.I))
    has_repro = bool(re.search(r"steps to reproduce|repro|reproduce", body, re.I))
    has_file_ref = bool(re.search(CODE_FILE_EXTENSION_RE, body))
    concrete_signals = sum([has_code_block, has_traceback, has_repro, has_file_ref])
    if concrete_signals == 0 and _word_count(body) > 15:
        reasons.append("no concrete signals (no code block, traceback, repro steps, or file reference): +20")
        return 20.0
    return 0.0


def _templated_structure_points(body: str, reasons: list) -> float:
    lowered = body.lower()
    header_hits = sum(1 for h in TEMPLATE_HEADERS if h in lowered)
    if header_hits >= 2:
        points = min(header_hits * 6, 18)
        reasons.append(f"templated section headers present ({header_hits}): +{points:.0f}")
        return points
    return 0.0


def _diff_line_stats(diff_text: str) -> dict:
    added = [l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]
    comment_or_blank = [
        l for l in added
        if not l[1:].strip() or l[1:].strip().startswith(("#", "//", "/*", "*", '"""', "'''"))
    ]
    return {"added": len(added), "comment_or_blank_added": len(comment_or_blank)}


def _diff_touched_files(diff_text: str) -> list:
    return re.findall(r"^\+\+\+ b/(.+)$", diff_text, re.M)


def _diff_padding_points(diff_text: str, reasons: list) -> float:
    if not diff_text.strip():
        return 0.0
    stats = _diff_line_stats(diff_text)
    if stats["added"] <= 10:
        return 0.0
    padding_ratio = stats["comment_or_blank_added"] / stats["added"]
    if padding_ratio > 0.4:
        points = min(padding_ratio * 40, 25)
        reasons.append(
            f"diff is mostly comments/blank padding "
            f"({stats['comment_or_blank_added']}/{stats['added']} added lines): +{points:.0f}"
        )
        return points
    return 0.0


def _diff_mismatch_points(body: str, diff_text: str, reasons: list) -> float:
    if not diff_text.strip():
        return 0.0
    mentioned_files = set(re.findall(CODE_FILE_EXTENSION_RE, body))
    touched_files = set(_diff_touched_files(diff_text))
    if mentioned_files and touched_files and mentioned_files.isdisjoint(touched_files):
        reasons.append(
            f"body references {sorted(mentioned_files)} but diff only touches {sorted(touched_files)}: +20"
        )
        return 20.0
    return 0.0


def classify(payload: dict) -> Verdict:
    """Heuristic classifier. `payload` needs `body`; PR payloads also carry `diff`."""
    body = payload.get("body", "") or ""
    diff_text = payload.get("diff", "") or ""
    reasons: list = []

    score = 0.0
    score += _boilerplate_points(body, reasons)
    score += _vague_language_points(body, reasons)
    score += _specificity_deficit_points(body, reasons)
    score += _templated_structure_points(body, reasons)
    score += _diff_padding_points(diff_text, reasons)
    score += _diff_mismatch_points(body, diff_text, reasons)

    score = min(score, 100.0)
    label = SLOP_LABEL if score >= SLOP_THRESHOLD else GENUINE_LABEL
    return Verdict(score=score, label=label, reasons=reasons)


def classify_with_claude(payload: dict) -> Verdict:
    """Same Verdict shape as classify(), backed by a Claude call.

    Only invoked when ANTHROPIC_API_KEY is set (see get_classifier()); the
    demo works fully offline without this path.
    """
    import json as _json

    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    body = payload.get("body", "") or ""
    diff_text = payload.get("diff", "") or ""
    prompt = (
        "You triage open-source contributions for signs of low-effort, "
        "AI-generated 'slop' (hallucinated fixes, generic boilerplate, "
        "diff/description mismatches) versus genuine human effort.\n\n"
        f"Title: {payload.get('title', '')}\n"
        f"Body:\n{body}\n\n"
        f"Diff:\n{diff_text or '(no diff -- this is an issue)'}\n\n"
        'Respond with ONLY compact JSON: {"score": <0-100 int, higher = more '
        'slop-like>, "label": "likely-ai-slop" or "human-effort", "reasons": '
        "[<short strings>]}"
    )
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _json.loads(message.content[0].text)
    return Verdict(score=float(data["score"]), label=data["label"], reasons=list(data.get("reasons", [])))


def get_classifier():
    """Returns the active classify function: Claude-backed if configured, else heuristic."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return classify_with_claude
    return classify
