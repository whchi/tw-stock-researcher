---
name: case-revisit
description: Use when returning to an existing stock case to summarize current status, open questions, data freshness, and next useful follow-ups.
---

# Case Revisit

Re-enter a case from repo files rather than memory. This is not a DAG stage in `workflow-contract.json` and owns no question namespace: it reconciles and reports on `open-questions.md`, but it may never call `open_questions.py upsert` or `resolve` itself — only the stage that owns a question's namespace may create or close it.

## Source Of Truth

- Follow `AGENTS.md` and `docs/data-layout.md`.
- Start from `stock-meta.json`, then read referenced case files.

## Workflow

1. Locate the single matching case folder.
2. Read `stock-meta.json`, `active-decisions.md`, `open-questions.md`, `signal-log.md`, and the latest core analysis files.
3. Run `.venv/bin/python scripts/workflow_state.py status <case_dir> --json` to see which stages are current, stale, or blocked, and `preflight` to see which stage should run next.
4. Summarize current research stance, unresolved questions, data freshness, and evidence timeline.
5. Identify which fetchers or stages should run next: `case-revisit → affected stages → their invalidated downstream stages → session-wrap`. Do not refresh data unless the user asked for an update.
6. If a question genuinely needs to be opened or closed, name which owning stage should run `open_questions.py upsert`/`resolve` — do not write to the ledger directly from this skill.

## Output

- A file-grounded status summary

## Verification

- Confirm every status claim is grounded in a case file or explicitly labeled as missing.
- Confirm stale data is reported with dates when available.
- Confirm no direct trade instruction language was introduced.
- Confirm this run did not call `open_questions.py upsert` or `resolve` directly.

## Red Lines

- Do not rely on chat memory as the source of truth.
- Do not auto-refresh all data without user intent.
- Do not collapse unresolved questions into conclusions.
- Do not close or create ledger questions from this skill; only an owning stage's resolver may.
