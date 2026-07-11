---
name: financial-data-fetch
description: Use when a stock case needs official-issuer, Goodinfo, or FinMind fundamentals data fetched or refreshed before financial-analysis can run.
---

# Financial Data Fetch

Refresh the structured financial-data layer that `financial-analysis` consumes. This stage owns network fetching for that layer; `financial-analysis` itself is a pure consumer of already-fetched artifacts.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `docs/source-policy.md`.
- `fetch_official_issuer.py` writes `official-issuer-data.json` (TWSE company master, monthly revenue, quarterly income summary — `docs/source-policy.md` tier `official`). Verified live: TWSE succeeds under strict TLS verification; TPEx's certificate currently fails verification and the fetch correctly reports `status: blocked` rather than bypassing TLS — this is an external TPEx issue, not a bug here.
- `fetch_fundamentals.py` writes `fundamentals-data.json` (FinMind official monthly revenue, quarterly IS/BS/CF, valuation band) — tier `secondary_aggregator`, reconciled against `official-issuer-data.json` via `scripts/reconcile_sources.py` where both cover the same metric/period.
- `fetch_goodinfo.py` writes `raw-data.json` as the temporary annual Goodinfo fallback/cross-check — tier `unofficial_scrape`.

## Commands

```bash
.venv/bin/python scripts/fetch_official_issuer.py <stock_id> --market TWSE --issuer-type general
.venv/bin/python scripts/fetch_fundamentals.py <stock_id>   # needs FIN_MIND_TOKEN
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
```

Use `--market TPEx` only for OTC issuers, and expect `status: blocked` until TPEx's certificate chain is fixed (see `docs/source-policy.md`). Use `--issuer-type financial` for banks/insurers/financial holding companies — the same TWSE dataset covers them, with non-applicable fields returned as `"--"`.

## Workflow

1. Confirm exactly one matching case folder exists.
2. Confirm the case folder exists; if not, run `stock-case-init` first.
3. Run the official-issuer adapter first (canonical when it succeeds), then the fundamentals fetcher (official monthly/quarterly layer), then Goodinfo as the annual fallback.
4. Read each output's `metadata.status`; a `blocked` required dataset means this fetch failed — report it, do not treat it as a silent pass.
5. Where `official-issuer-data.json` and `fundamentals-data.json` cover the same metric and period, reconcile with `scripts/reconcile_sources.py:reconcile_metric` before treating either as final. A `true_conflict` on a required metric opens a `FIN-DATA-CONFLICT-<slug>` question and blocks `financial-analysis`/`investment-thesis` from refreshing; other classifications (`rounding`, `period_mismatch`, `consolidation_mismatch`, `restatement`) are informational per `docs/source-policy.md` and never averaged.
6. Add unresolved data gaps to `open-questions.md`; close them only when the fetched data actually answers them.

## Output

- `official-issuer-data.json`
- `raw-data.json`
- `fundamentals-data.json`

## Verification

- Confirm no `<stock_id>_raw_data.json` or `<stock_id>_fundamentals_data.json` remains in repo root.
- Confirm the fetch did not write to repo root because of zero or multiple matching case folders.
- Confirm any data-gap question closed this run cites the evidence that answered it.

## Red Lines

- Do not let `financial-analysis` fetch data directly; all network fetching for this layer belongs here.
- Do not hide scraper or fetch warnings.
- Do not mark this stage `pass` when a required dataset is `blocked`.
- Do not disable TLS certificate verification for any official adapter. A TLS failure is a source failure — accept `status: blocked` for TPEx until the exchange fixes its certificate.
- Do not average a `true_conflict` between `official-issuer-data.json` and `fundamentals-data.json`; classify it and open a question instead.
