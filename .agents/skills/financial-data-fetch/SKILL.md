---
name: financial-data-fetch
description: Use when a stock case needs official-issuer, Goodinfo, or FinMind fundamentals data fetched or refreshed before financial-analysis can run.
---

# Financial Data Fetch

Refresh the structured financial-data layer that `financial-analysis` consumes. This stage owns network fetching for that layer; `financial-analysis` itself is a pure consumer of already-fetched artifacts.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `docs/source-policy.md` (once Task 8 lands).
- `fetch_fundamentals.py` writes `fundamentals-data.json` (official monthly revenue, quarterly IS/BS/CF, valuation band) — the primary monthly/quarterly source.
- `fetch_official_issuer.py` writes `official-issuer-data.json` (TWSE/TPEx official issuer, monthly revenue, IS/BS summaries) once implemented; until then this stage runs without it and `financial-analysis` treats it as absent.
- `fetch_goodinfo.py` writes `raw-data.json` as the temporary annual Goodinfo fallback/cross-check.

## Commands

```bash
.venv/bin/python scripts/fetch_fundamentals.py <stock_id>   # needs FIN_MIND_TOKEN
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
```

## Workflow

1. Confirm exactly one matching case folder exists.
2. Preflight: `.venv/bin/python scripts/workflow_state.py gate <case_dir> financial-data-fetch --as-of <YYYY-MM-DD> --json`; stop if `ready` is false and report `blocking_reasons`.
3. Run the fundamentals fetcher first (official monthly/quarterly layer), then the official-issuer adapter when available, then Goodinfo as the annual fallback.
4. Read each output's `metadata.status`; a `blocked` required dataset (see `workflow-contract.json` → `financial-data-fetch`) means this stage's own status is `blocked`, not silently `pass`.
5. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> financial-data-fetch`.
6. Track unresolved data gaps under question namespace `FIN-DATA` only: `.venv/bin/python scripts/open_questions.py upsert <case_dir> --stage financial-data-fetch --id FIN-DATA-<slug> ...`; close them only when a deterministic resolver predicate (`scripts/open_questions.py` → `resolve_three_statement_coverage`, `resolve_monthly_revenue_period`, `resolve_valuation_band_readiness`) is actually true.

## Output

- `official-issuer-data.json` (once implemented)
- `raw-data.json`
- `fundamentals-data.json`

## Verification

- Confirm no `<stock_id>_raw_data.json` or `<stock_id>_fundamentals_data.json` remains in repo root.
- Confirm the fetch did not write to repo root because of zero or multiple matching case folders.
- Confirm `workflow_state.py record` was run and the stage record's `status` matches what the fetch outputs actually report.
- Confirm any `FIN-DATA` question closed via `open_questions.py resolve` cites a deterministic evidence ref, not prose alone.

## Red Lines

- Do not let `financial-analysis` fetch data directly; all network fetching for this layer belongs here.
- Do not hide scraper or fetch warnings.
- Do not mark this stage `pass` when a required dataset is `blocked`.
