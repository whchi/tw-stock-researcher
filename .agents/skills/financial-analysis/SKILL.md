---
name: financial-analysis
description: Use when writing or refreshing financial-analysis.md with Goodinfo, FinMind, and MOPS-based operating, profitability, and balance-sheet analysis.
---

# Financial Analysis

Build the financial fact layer before quality, valuation, or thesis writing.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/financial-analysis.md`.
- Annual primary data is `raw-data.json` from `scripts/fetch_goodinfo.py`.
- Monthly revenue and quarterly statements come from `fundamentals-data.json` via `scripts/fetch_fundamentals.py`; Yahoo revenue is the fallback.
- Include MOPS cross-check links.

## Commands

```bash
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
.venv/bin/python scripts/fetch_fundamentals.py <stock_id>   # needs FIN_MIND_TOKEN
```

## Workflow

1. Confirm the case folder exists, then run the Goodinfo fetcher and the fundamentals fetcher first.
2. Read `raw-data.json`, especially `metadata`, `three_statement_coverage`, and sanity-check warnings; read `fundamentals-data.json` `metadata.warnings` for dataset gaps.
3. Fill the Recent 6M Revenue Snapshot from `fundamentals-data.json` → `derived.monthly_revenue_6m` (official source); fall back to `yahoo-data.json` revenue rows only when fundamentals data is missing, and label the fallback.
4. Fill the Quarterly Trend (8Q) table from `derived.quarterly_income_8q`; use `derived.quarterly_balance_key_items` and `derived.quarterly_cash_flow` for quarter-level working-capital and cash reads.
5. Write the 3D financial read: operating analysis, profitability analysis, and financial health.
6. Write period comparisons so the current period is the subject and prior periods are comparison baselines; state what changed in the current period before describing the baseline.
7. Include balance-sheet demand validation that reads revenue, receivables, inventory, payables, CFO, capex, and liquidity together.
8. Run four three-statement contradiction checks: revenue vs cash conversion, operating profit vs revenue, capex follow-through, and inventory-to-CFO lead. Label each evidence read `Confirming`, `Diverging`, `Watch`, or `Insufficient data`; these are research signals, not trade instructions.
9. Run accounting anomaly verification for related-party transactions, off-balance-sheet commitments, revenue-recognition policy changes, one-period line-item discontinuities, non-operating gains or losses, investment structure, and asset revaluation. Structured-data flags are candidates only: verify them in MOPS financial-statement notes or label the result `Low confidence` with the missing note named.
10. Put any `required_missing` coverage gaps under `Open Verification Items`; do not force a conclusion from incomplete data.

## Output

- `raw-data.json`
- `fundamentals-data.json`
- `financial-analysis.md`

## Verification

- Confirm `raw-data.json` and `fundamentals-data.json` exist in the case folder.
- Confirm no `<stock_id>_raw_data.json` or `<stock_id>_fundamentals_data.json` remains in repo root.
- Confirm the fetch did not write to repo root because of zero or multiple matching case folders.
- Confirm the 6M revenue snapshot cites the official fundamentals data or explicitly labels the Yahoo fallback.
- Confirm comparative conclusions use the current period as the grammatical and analytical subject.
- Confirm `financial-analysis.md` includes a MOPS official filing URL or an explicit missing-source note.
- Confirm all four three-statement contradiction checks have an evidence combination, a neutral signal label, and a source or missing-data note.
- Confirm every accounting-anomaly candidate is either checked against MOPS notes or explicitly labeled `Low confidence`; absence from Goodinfo or FinMind is not evidence that the anomaly is absent.
- Confirm any `three_statement_coverage.required_missing` fields appear in `Open Verification Items`.

## Red Lines

- Do not write financial analysis from Yahoo alone.
- Do not hide scraper warnings.
- Do not move judgment-layer conclusions into this fact layer.
