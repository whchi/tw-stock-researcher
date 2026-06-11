---
name: session-wrap
description: Use before ending a stock research session to preserve active decisions, unresolved questions, evidence timeline, and next review triggers.
---

# Session Wrap

Make the case resumable before stopping.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/active-decisions.md`, and `templates/open-questions.md`.

## Workflow

1. Read the files touched during the session.
2. Update `active-decisions.md` with current research stance, expected evidence timeline, thesis kill criteria, review triggers, and any user-provided position context.
3. Update `open-questions.md` with unresolved items, closed items, and evidence needed to resolve them.
4. Add a short next-step list that points to exact files or fetchers.
5. Keep all language neutral and research-focused.

## Output

- `active-decisions.md`
- `open-questions.md`
- Optional final session summary to the user

## Verification

- Confirm active decisions are evidence timelines and tracking criteria, not trade instructions.
- Confirm unresolved questions remain visible.
- Confirm the next session can resume from files without relying on chat memory.

## Red Lines

- Do not write direct entry, exit, stop-loss, position-sizing, or target-price instructions.
- Do not hide material missing data.
- Do not mark unresolved evidence as closed.
