This fixture is a copy of `../workflow-valid/` with one change: `yahoo-data.json`'s
`metadata.source_as_of` was bumped from `2026/06` to `2026/07`, so its on-disk hash no
longer matches the `output_hashes["yahoo-data.json"]` recorded in `stock-meta.json`'s
`stage_records.yahoo-profile-financials`.

This represents a case where an upstream fetcher was re-run (producing new data) but
`workflow_state.py record ... yahoo-profile-financials` has not been called yet to log
the change. Re-running `record` for `yahoo-profile-financials` against this fixture
should detect the output-hash drift and mark every transitive downstream consumer
(`company-deep-dive`, `financial-analysis`, `industry-transmission-analysis`,
`macro-impact-analysis`, `market-action-read` is unaffected since it depends on
`market-data-fetch` not `yahoo-profile-financials`, `quality-and-valuation-check`,
`investment-thesis`, `session-wrap`) as `stale`.
