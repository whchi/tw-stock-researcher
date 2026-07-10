---
name: session-wrap
description: Use before ending a stock research session to preserve active decisions, unresolved questions, evidence timeline, and next review triggers.
---

# Session Wrap

Make the case resumable before stopping. This is the terminal gate of the workflow DAG for both first visits and return visits: `research-html-output` requires a passing `session-wrap` gate, and a case is not "complete" until this stage's recorded status is `pass` or `degraded`.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/active-decisions.md`, and `templates/open-questions.md`.

## Workflow

1. Preflight: `.venv/bin/python scripts/workflow_state.py gate <case_dir> session-wrap --as-of <YYYY-MM-DD> --json`; if `ready` is false, finish `investment-thesis` first — do not wrap a session on an incomplete or stale thesis.
2. Read the files touched during the session, including the current `open-questions.md`.
3. Update `active-decisions.md` with current research stance, expected evidence timeline, thesis kill criteria, review triggers, and any user-provided position context. Missing `active-decisions.md` on a return visit is an explicit readiness error to surface, not a fallback opportunity.
4. Report unresolved and newly closed items from `open-questions.md`; you may `upsert` a `WRAP`-namespaced tracking question, but you may never call `open_questions.py resolve` — this stage reconciles and reports, it does not close questions on another stage's behalf.
5. Add a short next-step list that points to exact files or fetchers.
6. Keep all language neutral and research-focused.
7. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> session-wrap`.

## Return Visit Flow

`case-revisit` → affected stages → their invalidated downstream stages (per `workflow_state.py`'s stale cascade) → `session-wrap`. Re-running `session-wrap` after any upstream stage's output changes is what clears the case back to a current, recordable state.

## Output

- `active-decisions.md`
- Optional final session summary to the user

## Verification

- Confirm active decisions are evidence timelines and tracking criteria, not trade instructions.
- Confirm unresolved questions remain visible.
- Confirm the next session can resume from files without relying on chat memory.
- Confirm `workflow_state.py status <case_dir>` reports `complete: true` only when this stage's status is `pass` or `degraded`.

## Red Lines

- Do not write direct entry, exit, stop-loss, position-sizing, or target-price instructions.
- Do not hide material missing data.
- Do not mark unresolved evidence as closed.
- Do not call `open_questions.py resolve` from this stage; only the owning stage's resolver may close a question.
