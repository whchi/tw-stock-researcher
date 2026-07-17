---
name: session-wrap
description: Use before ending a stock research session to preserve active decisions, unresolved questions, evidence timeline, and next review triggers.
---

# Session Wrap

Make the case resumable before stopping.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/active-decisions.md`, and `templates/open-questions.md`.
- Read `stock-meta.json` and update its `updated_at`, `current_status`, and completed `file_references` before stopping.

## Workflow

1. Read the files touched during the session.
2. Update `active-decisions.md` with current research stance, expected evidence timeline, thesis kill criteria, review triggers, and any user-provided position context.
3. Complete the six-dimension research completeness gate in `active-decisions.md`: Business, Risk, Financial, Quality Signal, Forward-Looking, and Internal Consistency. Score only from cited case evidence, then record every critical gap and its concrete remedy.
4. Update `open-questions.md` with unresolved items, closed items, and evidence needed to resolve them.
5. Add a short next-step list that points to exact files or fetchers.
6. Keep all language neutral and research-focused.

## Output

- `active-decisions.md`
- `open-questions.md`
- Updated `stock-meta.json`
- Optional final session summary to the user

## Verification

- Confirm active decisions are evidence timelines and tracking criteria, not trade instructions.
- Confirm all six completeness dimensions have a 0-10 score, evidence basis, and visible gap; confirm each critical gap has a source or skill-based remedy.
- Confirm unresolved questions remain visible.
- Confirm the next session can resume from files without relying on chat memory.

## Red Lines

- Do not write direct entry, exit, stop-loss, position-sizing, or target-price instructions.
- Do not hide material missing data.
- Do not mark unresolved evidence as closed.
