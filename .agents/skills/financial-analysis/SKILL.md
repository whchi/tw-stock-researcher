---
name: financial-analysis
description: Use when writing or refreshing financial-analysis.md with Goodinfo/MOPS-based operating, profitability, and balance-sheet analysis.
---

# Financial Analysis

Build the financial fact layer before quality, valuation, or thesis writing.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/financial-analysis.md`.
- Primary data is `raw-data.json` from `scripts/fetch_goodinfo.py`.
- Include MOPS cross-check links.

## Command

```bash
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
```

## Workflow

1. Confirm the case folder exists, then run the Goodinfo fetcher first.
2. Read `raw-data.json`, especially `metadata`, `three_statement_coverage`, and sanity-check warnings.
3. Write the 3D financial read: operating analysis, profitability analysis, and financial health.
4. Include balance-sheet demand validation that reads revenue, receivables, inventory, payables, CFO, capex, and liquidity together.
5. Put any `required_missing` coverage gaps under `Open Verification Items`; do not force a conclusion from incomplete data.

## Output

- `raw-data.json`
- `financial-analysis.md`

## Verification

- Confirm `raw-data.json` exists in the case folder.
- Confirm no `<stock_id>_raw_data.json` remains in repo root.
- Confirm `financial-analysis.md` includes a MOPS official filing URL or an explicit missing-source note.

## Red Lines

- Do not write financial analysis from Yahoo alone.
- Do not hide scraper warnings.
- Do not move judgment-layer conclusions into this fact layer.
