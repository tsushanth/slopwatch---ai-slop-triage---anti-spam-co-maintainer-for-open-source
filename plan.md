# Slopwatch — Local MVP Scaffold Plan

## Goal of this scaffold

Prove the core value — "given an issue/PR's text + diff, classify it as
low-effort AI-slop vs. genuine human effort, then decide a triage action
(label / request-clarification / close) and draft a first-response reply" —
running entirely on a laptop against saved sample payloads. No GitHub App
install, no webhooks, no server, no database, no billing.

## 1. Stack

**Plain Python 3 script(s), stdlib only, run via CLI.**

- No web framework, no GitHub App SDK (Probot/octokit), no database, no
  Docker.
- Classification is a deterministic, inspectable **rule/heuristic scorer**
  (boilerplate-phrase detection, description-vs-diff mismatch, genericness
  of language, churn-to-substance ratio, templated-PR-body detection) —
  this is the part that needs to be demoed and iterated on, so it must be
  transparent and runnable with zero API keys.
- Optional: if `ANTHROPIC_API_KEY` is set in the environment, one function
  swaps the heuristic score for a Claude call (via the `anthropic` package)
  that returns the same structured verdict. This is a single, isolated
  function — the demo works fully offline without it. Not required to
  prove the idea; included only to show the upgrade path.
- Why this stack: the idea's core value is a classification + decision
  function over text, not an integration. A CLI over local JSON fixtures
  exercises that function directly with the fastest iteration loop and
  zero infra.

## 2. Explicitly out of scope for this scaffold

- GitHub App registration, webhooks, OAuth, installation tokens.
- Any live GitHub API calls (posting comments, applying labels, closing
  issues/PRs for real). The tool prints/writes what it *would* do.
- Hosting/deployment, background workers, queues, schedulers.
- Accounts, multi-tenancy, per-repo config storage.
- Billing/subscription/Stripe.
- A database — fixtures and outputs are flat JSON files on disk.
- A real diff parser / language-aware code analysis — the heuristic works
  off the raw unified diff text and PR/issue body text only.
- UI of any kind — CLI output (stdout + a written JSON/Markdown report)
  is sufficient to demonstrate the value.

None of these are needed to demonstrate "does this correctly separate
slop from genuine contributions and pick a sane triage action" — that
claim can be fully tested against static sample data.

## 3. File / directory layout

```
slopwatch/
  cli.py                # entry point: `python -m slopwatch.cli fixtures/*.json`
  classifier.py          # heuristic scoring fn; optional Claude-backed fn behind same interface
  triage.py              # maps classification -> action (label/clarify/close) + drafts reply text
  fixtures/
    genuine_issue.json    # sample real bug report (GitHub issue payload subset)
    genuine_pr.json        # sample real, well-scoped PR
    slop_pr_verbose.json   # sample bloated AI-generated PR with hallucinated fix
    slop_issue_vague.json  # sample vague/templated AI-generated issue
  out/
    report.json            # last run's verdicts + drafted replies (generated, gitignored)
  tests/
    test_classifier.py     # unit tests on each fixture's expected verdict
    test_triage.py          # unit tests on action-mapping + reply drafting
  plan.md                 # this file
  README.md                # how to run the demo (written alongside code, not now)
```

## 4. Verification

- **Unit tests** (`pytest tests/`): each fixture in `fixtures/` has a
  known expected classification (slop vs. genuine) and expected triage
  action; tests assert the classifier and triage functions produce them.
  This is the primary correctness check and needs no API key.
- **Manual run-through**:
  ```
  python -m slopwatch.cli fixtures/*.json
  ```
  Inspect stdout (and `out/report.json`) to confirm each sample gets a
  sensible verdict, action, and drafted reply — e.g. `slop_pr_verbose.json`
  → labeled `likely-ai-slop`, action `request-clarification`, with a
  drafted reply asking for a minimal repro; `genuine_pr.json` → labeled
  `human-effort`, action `none`, no reply drafted.
- **Optional live check**: re-run with `ANTHROPIC_API_KEY` set to confirm
  the Claude-backed path returns the same verdict shape as the heuristic
  path (schema parity, not accuracy grading).
