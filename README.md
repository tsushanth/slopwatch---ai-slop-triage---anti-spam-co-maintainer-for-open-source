# Slopwatch — AI-Slop Triage & Anti-Spam Co-Maintainer (local MVP scaffold)

Slopwatch is a GitHub App concept that sits in front of a repo's issues and
PRs and specifically classifies low-effort, plausible-looking AI-generated
contributions (verbose diffs, hallucinated fixes, vague/templated
descriptions) versus genuine human effort — then auto-triages: label,
request clarification, or close spam, and drafts first-response replies for
real issues. It's narrower than general AI code review tools (CodeRabbit,
PR-Agent, Copilot code review), which grade code quality on every PR;
Slopwatch's job is specifically the spam/slop classification and lifecycle
triage step.

This directory is a **local scaffold** that proves the core value with zero
infrastructure: given an issue/PR's text (and diff, for PRs), it classifies
the contribution, picks a triage action, and drafts a reply — all against
static JSON fixtures on your laptop. See `plan.md` for the full scope and
what's deliberately excluded (no GitHub App install, no webhooks, no
server, no database, no live GitHub API calls, no billing).

## How it works

- **`slopwatch/classifier.py`** — a deterministic, inspectable heuristic
  scorer. It looks for boilerplate AI phrasing, vague/generic language
  density, missing concrete signals (no repro steps, no traceback, no file
  references), templated section headers (`## Summary`, `## Changes`, ...),
  and — for PRs — diff padding (mostly comments/blank lines) and
  description-vs-diff mismatches (body claims to touch a file the diff
  never touches, i.e. a "hallucinated fix"). Each signal that fires is
  recorded as a human-readable reason string alongside its point
  contribution, so a verdict is always explainable, not a black box.
  Score >= 50 → `likely-ai-slop`, otherwise `human-effort`.
- **`slopwatch/triage.py`** — maps a verdict to an action:
  - `human-effort` + issue → `draft-reply` (friendly first response)
  - `human-effort` + PR → `none` (goes to normal human review)
  - `likely-ai-slop`, score < 80 → `request-clarification` (asks for repro
    steps / the specific bug / a test, and says why it was flagged)
  - `likely-ai-slop`, score >= 80 → `close` (explains why, invites a
    resubmission with detail)
- **`slopwatch/cli.py`** — reads fixture JSON files, runs the classifier and
  triage functions, prints a verdict + drafted reply per fixture, and
  writes the full result set to `out/report.json`. It never calls the
  GitHub API — it only prints/writes what the bot *would* do.

Optional upgrade path: if `ANTHROPIC_API_KEY` is set in your environment,
`slopwatch/classifier.py` swaps in `classify_with_claude()`, which asks
Claude to return the same verdict shape (score/label/reasons) instead of
using the heuristic. This isn't required to prove the idea — the demo runs
fully offline without it.

## Running it

Requires Python 3.9+ and (for tests) `pytest`. No other dependencies for
the offline path.

```bash
# Run the classifier + triage over all sample fixtures
python -m slopwatch.cli fixtures/*.json

# Inspect the same results as structured JSON
cat out/report.json

# Run the unit tests (expected classification/action per fixture)
pytest tests/
```

### Fixtures

| File                          | Expected verdict     | Expected action          |
|-------------------------------|-----------------------|---------------------------|
| `fixtures/genuine_issue.json`  | `human-effort`         | `draft-reply`              |
| `fixtures/genuine_pr.json`     | `human-effort`         | `none`                      |
| `fixtures/slop_pr_verbose.json`| `likely-ai-slop` (<80) | `request-clarification`    |
| `fixtures/slop_issue_vague.json`| `likely-ai-slop` (>=80)| `close`                    |

### Optional: try the Claude-backed classifier

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python -m slopwatch.cli fixtures/*.json
```

This confirms the Claude path returns the same verdict shape as the
heuristic (schema parity, not an accuracy grading exercise).

## Out of scope for this scaffold

GitHub App registration/webhooks/OAuth, live GitHub API calls, hosting,
accounts/multi-tenancy, billing, a database, a real diff parser, and any
UI. See `plan.md` for the reasoning.
