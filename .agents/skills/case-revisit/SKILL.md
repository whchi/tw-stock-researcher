---
name: case-revisit
description: Use when returning to an existing stock case to summarize current status, open questions, data freshness, and next useful follow-ups.
---

# Case Revisit

Re-enter a case from repo files rather than memory. This skill reports on `open-questions.md`; opening or closing questions belongs to the analysis stages themselves.

## Source Of Truth

- Follow `AGENTS.md` and `docs/data-layout.md`.
- Start from `stock-meta.json`, then read referenced case files.

## Workflow

1. Locate the single matching case folder.
2. Read `stock-meta.json`, `active-decisions.md`, `open-questions.md`, `signal-log.md`, and the latest core analysis files.
3. Compare each artifact's `updated_at` / `fetched_at` dates against today to judge which data is stale.
4. Summarize current research stance, unresolved questions, data freshness, and evidence timeline.
5. Identify which fetchers or stages should run next: `case-revisit → affected stages → session-wrap`. Do not refresh data unless the user asked for an update.
6. If a question genuinely needs to be opened or closed, note it in the summary for the relevant analysis stage to handle.

## Output

- A file-grounded status summary

## Verification

- Confirm every status claim is grounded in a case file or explicitly labeled as missing.
- Confirm stale data is reported with dates when available.
- Confirm no direct trade instruction language was introduced.

## Red Lines

- Do not rely on chat memory as the source of truth.
- Do not auto-refresh all data without user intent.
- Do not collapse unresolved questions into conclusions.
- Do not close or create open questions from this skill.
