---
name: signal-update
description: Use when new revenue, filings, news, user-provided data, or market events need to be appended to a stock case and assessed for thesis impact.
---

# Signal Update

Record new information without rewriting the whole case unless the evidence truly changes it. Like `case-revisit`, this is not a DAG stage and owns no question namespace, so it may not call `open_questions.py upsert` or `resolve` directly.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/signal-log.md`, and `templates/thesis-updates.md`.
- `signal-log.md` is append-only.

## Workflow

1. Classify the new item: verified fact, management claim, market inference, speculation to verify, or user-provided context.
2. Append the event to `signal-log.md` with date, source, classification, price reaction if relevant, validation status, thesis impact, and next action.
3. Refresh the relevant fetcher only when the signal depends on updated structured data; refreshing an upstream fetch and re-running its skill's `workflow_state.py record` will cascade the correct stages to `stale` automatically.
4. Update `thesis-updates.md` when the signal changes the research stance. For `investment-memo.md` or `active-decisions.md`, prefer flagging `investment-thesis` or `session-wrap` to re-run over hand-editing those files directly, since each has a single owning stage.
5. Label user-provided data as user-provided until fetched or independently verified.

## Output

- `signal-log.md`
- Optional `thesis-updates.md`

## Verification

- Confirm the signal was appended rather than replacing history.
- Confirm changed thesis language is traceable to the new evidence.
- Confirm no direct trade instruction language was introduced.
- Confirm this run did not call `open_questions.py upsert` or `resolve` directly, and did not bypass `investment-thesis`/`session-wrap` ownership of their files.

## Red Lines

- Do not silently overwrite prior signal history.
- Do not treat user-provided numbers as verified unless checked.
- Do not update unrelated case layers just to make the file set look fresh.
- Do not hand-edit `investment-memo.md` or `active-decisions.md`; flag the owning stage to re-run instead.
