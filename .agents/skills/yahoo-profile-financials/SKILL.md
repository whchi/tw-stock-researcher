---
name: yahoo-profile-financials
description: Use when a stock case needs Yahoo Finance Taiwan profile, revenue, income statement, cash-flow, or supplemental financial data fetched or refreshed.
---

# Yahoo Profile Financials

Fetch Yahoo data as the company profile and supplemental financial input layer.

## Source Of Truth

- Follow `AGENTS.md` and `docs/data-layout.md`.
- Use the existing case folder under `companies/<stock_id>-*/`.
- Yahoo data supports `company-deep-dive`; Goodinfo and MOPS remain the primary financial-analysis source.

## Command

```bash
.venv/bin/python scripts/fetch_yahoo.py <stock_id>
```

Use `--suffix TWO` only when Yahoo requires the OTC `.TWO` symbol.

## Workflow

1. Confirm a single matching case folder exists before running the script.
2. Run the fetcher with the repo-local virtualenv.
3. Read `yahoo-data.json` and note data freshness, missing fields, warning flags, and market suffix used.
4. Use the data only as verified or source-labeled support in downstream markdown.

## Output

- `companies/<ticker-slug>/yahoo-data.json`

## Verification

- Confirm `yahoo-data.json` exists in the case folder.
- Confirm no `<stock_id>_yahoo_data.json` remains in repo root.
- Confirm any missing profile, revenue, income, or cash-flow fields are surfaced before analysis.

## Red Lines

- Do not treat Yahoo as the primary audited financial source.
- Do not fill missing data from memory.
- Do not persist credentials or tokens for this step.
