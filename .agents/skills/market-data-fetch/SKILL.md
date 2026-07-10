---
name: market-data-fetch
description: Use when a stock case needs market-data.json or tdcc-data.json refreshed for price-volume, institutional flow, holder distribution, margin, short-sale, day-trading, or egg-theory analysis.
---

# Market Data Fetch

Refresh the market-action data layer while preserving the user's stock-id workflow.

## Source Of Truth

- Follow `AGENTS.md` and `docs/data-layout.md`.
- `fetch_tdcc.py` writes `tdcc-data.json`; `fetch_finmind.py` writes `market-data.json`.
- `fetch_finmind.py` may read local `tdcc-data.json` as the holder-distribution snapshot for egg-theory proxy reads.

## Commands

```bash
.venv/bin/python scripts/fetch_tdcc.py <stock_id>
.venv/bin/python scripts/fetch_finmind.py <stock_id>
```

If FinMind needs credentials, provide `FIN_MIND_TOKEN` only in the command environment for that run; do not write it into repo files.

## Workflow

1. Preflight: `.venv/bin/python scripts/workflow_state.py gate <case_dir> market-data-fetch --as-of <YYYY-MM-DD> --json`; if `ready` is false, run `stock-case-init` first.
2. Run TDCC first so holder distribution is available before FinMind derivation. The all-market CSV is cached under `market/` (72h default; `--refresh` forces a re-download), and each new snapshot date is appended to `tdcc-data.json` `history`.
3. If TDCC fails, record the failure and continue to FinMind only when price-volume data is still useful for the requested read.
4. Run FinMind second to refresh price, volume, institutional flow, margin, shareholding, day-trading, and egg-theory derived reads.
5. Inspect warnings for permission limits, especially `TaiwanStockHoldingSharesPer`; when it is unavailable, holder trends come from accumulated TDCC history (`holder_trend_from_tdcc_weekly`, confidence capped at medium) and need at least two snapshot dates in the window.
6. Keep TDCC `id=1-5` concept clear: it is the all-market ownership distribution dataset id, not a stock id.
7. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> market-data-fetch`.
8. Track unresolved market-data gaps under question namespace `MKT-DATA` only via `scripts/open_questions.py upsert <case_dir> --stage market-data-fetch --id MKT-DATA-<slug> ...`; close 5-day/6-month window and TDCC-history questions only via `resolve_market_price_5d_window`, `resolve_market_history_6m_window`, or `resolve_tdcc_history_length`.

## Output

- `tdcc-data.json`
- `market-data.json`

## Verification

- Confirm both files are in the case folder when TDCC succeeds.
- Confirm no `<stock_id>_tdcc_data.json` or `<stock_id>_market_data.json` remains in repo root.
- Confirm the fetchers did not write to repo root because of zero or multiple matching case folders.
- Confirm `market-data.json` contains `derived.egg_theory_read` for `1m`, `3m`, and `6m` when enough price rows exist.
- Confirm missing holder history caps confidence and is surfaced as a warning or note.

## Red Lines

- Do not hardcode a stock id inside the fetch flow.
- Do not scrape via browser when the scripts can fetch the data.
- Do not let FinMind permission errors fail the whole workflow when fallback data is available.
