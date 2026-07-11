---
name: session-wrap
description: Use before ending a stock research session to preserve active decisions, unresolved questions, evidence timeline, and next review triggers.
---

# Session Wrap

Make the case resumable before stopping. This is the last step of every session, first visit or return visit; run it before any HTML output.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/active-decisions.md`, and `templates/open-questions.md`.

## Workflow

1. Confirm `investment-memo.md` reflects this session's evidence; if the thesis is unfinished, finish `investment-thesis` first — do not wrap a session on an incomplete or stale thesis.
2. Read the files touched during the session, including the current `open-questions.md`.
3. Update `active-decisions.md` with current research stance, expected evidence timeline, thesis kill criteria, review triggers, and any user-provided position context. Missing `active-decisions.md` on a return visit is an explicit readiness error to surface, not a fallback opportunity.
4. Report unresolved and newly closed items from `open-questions.md`; this stage reconciles and reports, it does not close questions on another stage's behalf.
5. Add a short next-step list that points to exact files or fetchers.
6. Keep all language neutral and research-focused.

## Return Visit Flow

`case-revisit` → affected stages → `session-wrap`. Re-run `session-wrap` after any upstream stage's output changes so the case closes on current evidence.

## Output

- `active-decisions.md`
- Optional final session summary to the user

## Verification

- Confirm active decisions are evidence timelines and tracking criteria, not trade instructions.
- Confirm unresolved questions remain visible.
- Confirm the next session can resume from files without relying on chat memory.

## Red Lines

- Do not write direct entry, exit, stop-loss, position-sizing, or target-price instructions.
- Do not hide material missing data.
- Do not mark unresolved evidence as closed.
- Do not close another stage's open questions from this stage.
