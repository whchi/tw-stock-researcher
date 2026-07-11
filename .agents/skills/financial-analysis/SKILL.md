---
name: financial-analysis
description: Use when writing or refreshing financial-analysis.md with Goodinfo/MOPS-based operating, profitability, and balance-sheet analysis.
---

# Financial Analysis

Build the financial fact layer before quality, valuation, or thesis writing. This skill does not fetch data itself; `financial-data-fetch` owns that.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/financial-analysis.md`.
- Annual primary data is `raw-data.json` (from `financial-data-fetch`).
- Monthly revenue and quarterly statements come from `fundamentals-data.json`; Yahoo revenue is the fallback.
- Include MOPS cross-check links.

## Workflow

1. Confirm `company-analysis.md` and the fetched data (`fundamentals-data.json` / `raw-data.json`) exist; if missing, run `company-deep-dive` / `financial-data-fetch` first.
2. Read `raw-data.json`, especially `metadata`, `three_statement_coverage`, and sanity-check warnings; read `fundamentals-data.json` `metadata.warnings` for dataset gaps.
3. Fill the Recent 6M Revenue Snapshot from `fundamentals-data.json` → `derived.monthly_revenue_6m` (official source); fall back to `yahoo-data.json` revenue rows only when fundamentals data is missing, and label the fallback.
4. Fill the Quarterly Trend (8Q) table from `derived.quarterly_income_8q`; use `derived.quarterly_balance_key_items` and `derived.quarterly_cash_flow` for quarter-level working-capital and cash reads.
5. Write the 3D financial read: operating analysis, profitability analysis, and financial health.
6. Include balance-sheet demand validation that reads revenue, receivables, inventory, payables, CFO, capex, and liquidity together.
7. Put any `required_missing` coverage gaps under `Open Verification Items`; do not force a conclusion from incomplete data.
8. Add unresolved analysis gaps to `open-questions.md`.

## Output

- `financial-analysis.md`

## Verification

- Confirm `raw-data.json` and `fundamentals-data.json` already exist in the case folder before writing (from `financial-data-fetch`); this skill does not create them.
- Confirm the 6M revenue snapshot cites the official fundamentals data or explicitly labels the Yahoo fallback.
- Confirm `financial-analysis.md` includes a MOPS official filing URL or an explicit missing-source note.
- Confirm any `three_statement_coverage.required_missing` fields appear in `Open Verification Items`.

## Red Lines

- Do not fetch data from this skill; run `financial-data-fetch` first when data is missing or stale.
- Do not write financial analysis from Yahoo alone.
- Do not hide scraper warnings.
- Do not move judgment-layer conclusions into this fact layer.
