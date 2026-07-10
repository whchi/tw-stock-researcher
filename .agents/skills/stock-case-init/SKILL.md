---
name: stock-case-init
description: Use when starting a new Taiwan stock research case or when a requested stock has no case folder yet.
---

# Stock Case Init

Create the durable case shell before any fetch or analysis work.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `DISCLAIMER.md`.
- Use `templates/stock-meta.json`, `templates/research-questions.md`, and `templates/open-questions.md`.
- Case path is `companies/<stock_id>-<slug>/`.

## Workflow

1. Check whether exactly one `companies/<stock_id>-*/` folder already exists.
2. If multiple matches exist, stop and ask which case folder is authoritative before writing.
3. If none exists, create `companies/<stock_id>-<slug>/` using a stable, readable slug.
4. Copy the needed template shapes into the case folder and fill only facts known from the user or verified repo data.
5. In `stock-meta.json`, keep `file_references` values either `null` or repo-relative case paths.
6. Seed `research-questions.md` with core business questions, disconfirming evidence to seek, and a claim hygiene register.
7. Seed `open-questions.md` with the canonical Active/Resolved tables from `templates/open-questions.md` (do not hand-write a different shape); add unresolved items that should carry across sessions with `scripts/open_questions.py upsert <case_dir> --stage stock-case-init --id CASE-<slug> ...`.
8. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> stock-case-init`.

## Output

- `stock-meta.json`
- `research-questions.md`
- `open-questions.md`

## Verification

- Confirm there is exactly one matching case folder for the stock id.
- Confirm `stock-meta.json` has no absolute paths.
- Confirm every non-null `file_references` value is rooted in the case folder.
- Confirm no root fallback files such as `<stock_id>_raw_data.json`, `<stock_id>_yahoo_data.json`, or `<stock_id>_market_data.json` were created.
- Confirm `scripts/open_questions.py validate <case_dir>/open-questions.md` passes and `workflow_state.py record` logged this stage.

## Red Lines

- Do not invent company facts.
- Do not run fetchers before the case folder exists.
- Do not overwrite an existing case without explicit user approval.
