---
name: investment-thesis
description: Use when writing or refreshing investment-memo.md with Bull/Base/Bear scenarios, business thesis, pricing thesis, and expectation-gap analysis.
---

# Investment Thesis

Synthesize the case without collapsing evidence, judgment, and market pricing into one blob. This skill is the sole writer of `investment-memo.md`; it writes the whole memo once per refresh rather than accepting row-level backfills from other stages.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/investment-memo.md`, and `investment-reasoning-framework.md`.
- Read `quality-and-valuation-check.md` and a current `market-action-read.md` before writing the memo.

## Workflow

1. Preflight: `.venv/bin/python scripts/workflow_state.py gate <case_dir> investment-thesis --as-of <YYYY-MM-DD> --json`; if `ready` is false, run or wait on the listed upstream stages (company-deep-dive, financial-analysis, industry-transmission-analysis, macro-impact-analysis, quality-and-valuation-check, market-action-read) instead of writing a memo from stale evidence.
2. Read the current company, financial, industry, macro, quality, and market-action layers.
3. Write the dual framework: Business Thesis and Pricing Thesis.
4. Include Bull/Base/Bear scenarios with probability weights, EPS or driver assumptions, and scenario-derived price ranges; anchor scenario multiples to the `fundamentals-data.json` valuation band rather than remembered multiples.
5. Explain expectation gaps: market belief, verified evidence, narrative-only claims, and verification needed.
6. Summarize evidence support without duplicating raw tables from other layers, including the current market-action read.
7. Capture critical unresolved questions and non-portable claims.
8. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> investment-thesis`.
9. Track unresolved thesis questions under question namespace `THESIS` only via `scripts/open_questions.py upsert <case_dir> --stage investment-thesis --id THESIS-<slug> ...`.

## Output

- `investment-memo.md`

## Verification

- Confirm every scenario-derived range is tied to explicit assumptions.
- Confirm scenario multiple assumptions cite valuation-band context when `fundamentals-data.json` provides it.
- Confirm the memo does not duplicate full financial, macro, quality, or market-action tables.
- Confirm the memo's market-action evidence reflects a current `market-action-read.md`, not a stale or empty backfill.
- Confirm disclaimer language and no-advice wording are present.

## Red Lines

- Do not write unsupported price targets.
- Do not use imperative recommendation language.
- Do not treat narrative expansion as fundamental validation.
- Do not accept a partial row backfill from `market-action-read`; read the file and write the whole memo yourself.
