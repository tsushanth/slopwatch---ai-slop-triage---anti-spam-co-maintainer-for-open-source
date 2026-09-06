"""CLI entry point: python -m slopwatch.cli fixtures/*.json

Runs the heuristic (or Claude-backed) classifier and the triage
decision function against local JSON fixtures, prints a verdict per
fixture, and writes the full result set to out/report.json. No live
GitHub calls are made -- this only prints/writes what the bot *would* do.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from slopwatch.classifier import get_classifier
from slopwatch.triage import decide

OUT_PATH = Path("out/report.json")


def run(paths: list) -> list:
    classify = get_classifier()
    results = []
    for path in paths:
        payload = json.loads(Path(path).read_text())
        kind = payload.get("type", "issue")
        verdict = classify(payload)
        triage = decide(verdict, kind)
        results.append({
            "file": str(path),
            "kind": kind,
            "title": payload.get("title", ""),
            "score": verdict.score,
            "label": verdict.label,
            "reasons": verdict.reasons,
            "action": triage.action,
            "reply": triage.reply,
        })
    return results


def _print_result(r: dict) -> None:
    print(f"\n{r['file']}  [{r['kind']}]  {r['title']!r}")
    print(f"  score={r['score']:.0f}  label={r['label']}  action={r['action']}")
    for reason in r["reasons"]:
        print(f"    - {reason}")
    if r["reply"]:
        print(f"  drafted reply:\n    {r['reply']}")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m slopwatch.cli <fixture.json> [...]", file=sys.stderr)
        return 1

    results = run(argv)
    for r in results:
        _print_result(r)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
