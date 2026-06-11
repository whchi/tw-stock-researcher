---
name: case-revisit
description: Use when returning to an existing stock case to summarize current status, open questions, data freshness, and next useful follow-ups.
---

# Case Revisit

Re-enter a case from repo files rather than memory.

## Source Of Truth

- Follow `AGENTS.md` and `docs/data-layout.md`.
- Start from `stock-meta.json`, then read referenced case files.

## Workflow

1. Locate the single matching case folder.
2. Read `stock-meta.json`, `active-decisions.md`, `open-questions.md`, `signal-log.md`, and the latest core analysis files.
3. Summarize current research stance, unresolved questions, data freshness, and evidence timeline.
4. Identify which fetchers or skills should run next, but do not refresh data unless the user asked for an update.
5. Carry forward closed and unresolved questions into `open-questions.md` when needed.

## Output

- A file-grounded status summary
- Optional updates to `open-questions.md`

## Verification

- Confirm every status claim is grounded in a case file or explicitly labeled as missing.
- Confirm stale data is reported with dates when available.
- Confirm no direct trade instruction language was introduced.

## Red Lines

- Do not rely on chat memory as the source of truth.
- Do not auto-refresh all data without user intent.
- Do not collapse unresolved questions into conclusions.
