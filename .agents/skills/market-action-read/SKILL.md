---
name: market-action-read
description: Use when writing or refreshing market-action-read.md from market-data.json and tdcc-data.json as a neutral market-state evidence layer.
---

# Market Action Read

Turn refreshed market data into a neutral read, not a trading decision.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `docs/data-freshness.md`, and `templates/market-action-read.md`.
- Run or verify `market-data-fetch` first when data is missing or stale.

## Workflow

1. Read `market-data.json`; read `tdcc-data.json` when present.
2. Cover 1D/3D/5D price-volume and institutional-flow windows.
3. Add egg-theory reads for `1m`, `3m`, and `6m` when `derived.egg_theory_read` exists.
4. Surface holder-distribution limits clearly: `snapshot_only`, missing `TaiwanStockHoldingSharesPer`, or insufficient holder trend means confidence cannot be high.
5. Use neutral labels such as `market confirmation`, `price-in risk`, `thesis validation trigger`, `assumption failure signal`, and `wait_for_confirmation`.
6. After `market-action-read.md` is complete, automatically run research-html-output for the same case folder so the derived `research-summary-data.json` and `research-summary.html` are refreshed as the final workflow artifact.

## Output

- `market-action-read.md`
- `research-summary-data.json` and `research-summary.html` refreshed via `research-html-output`

## Verification

- Confirm the file cites `market-data.json` and TDCC/FinMind datasets used.
- Confirm `research-summary-data.json` is valid JSON and `research-summary.html` exists in the same company folder.
- Confirm the rendered HTML contains no unresolved template placeholders.
- Confirm no direct entry, exit, stop-loss, position-sizing, target-price, or buy/sell instruction language was introduced.
- Confirm egg-theory labels are research labels: `supply_demand_favorable`, `wait_for_confirmation`, or `supply_demand_risk`.

## Red Lines

- Do not convert A1/B3 into direct purchase advice.
- Do not hide missing holder history.
- Do not use action-like labels such as `Avoid`.
