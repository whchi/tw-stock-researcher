---
name: market-action-read
description: Use when writing or refreshing market-action-read.md from market-data.json and tdcc-data.json as a neutral market-state evidence layer.
---

# Market Action Read

Turn refreshed market data into a neutral read, not a trading decision. This skill owns only `market-action-read.md`; it never edits `investment-memo.md` — `investment-thesis` reads this file directly and writes the whole memo once.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, and `templates/market-action-read.md`.
- Run or verify `market-data-fetch` first when data is missing or stale.

## Workflow

1. Confirm `market-data.json` exists; if missing, run `market-data-fetch` first.
2. Read `market-data.json`; read `tdcc-data.json` when present.
3. Cover 1D/3D/5D price-volume and institutional-flow windows.
4. Add egg-theory reads for `1m`, `3m`, and `6m` when `derived.egg_theory_read` exists.
5. Surface holder-distribution limits clearly: `snapshot_only`, missing `TaiwanStockHoldingSharesPer`, or insufficient holder trend means confidence cannot be high.
6. Use neutral labels such as `market confirmation`, `price-in risk`, `thesis validation trigger`, `assumption failure signal`, and `wait_for_confirmation`.
7. Add unresolved market-read gaps to `open-questions.md`.

## Output

- `market-action-read.md`

## Verification

- Confirm the file cites `market-data.json` and TDCC/FinMind datasets used.
- Confirm this run did not write to `investment-memo.md`.
- Confirm no direct entry, exit, stop-loss, position-sizing, target-price, or buy/sell instruction language was introduced.
- Confirm egg-theory labels are research labels: `supply_demand_favorable`, `wait_for_confirmation`, or `supply_demand_risk`.

## Red Lines

- Do not write or backfill any row in `investment-memo.md`; that ownership belongs to `investment-thesis` alone.
- Do not convert A1/B3 into direct purchase advice.
- Do not hide missing holder history.
- Do not use action-like labels such as `Avoid`.
