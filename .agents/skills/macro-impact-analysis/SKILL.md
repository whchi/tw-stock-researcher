---
name: macro-impact-analysis
description: Use when deciding which macro variables matter to a stock case and writing or refreshing macro-map.md.
---

# Macro Impact Analysis

Keep only macro variables with a concrete path into the company case.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, `docs/data-freshness.md`, and `templates/macro-map.md`.
- Shared reusable context may live in `market/shared-macro-view.md`.

## Command

```bash
.venv/bin/python scripts/fetch_macro.py
```

Run this when `market/shared-macro-data.json` is missing or stale.

## Workflow

1. Check `market/shared-macro-data.json` freshness; refresh shared macro data when it is missing, stale, or the user asked for a fresh macro read.
2. Read the company case to identify revenue, margin, cash-flow, valuation, and narrative sensitivities.
3. Include only macro variables with a clear transmission path.
4. Explicitly exclude popular but immaterial variables and state what evidence would make them relevant.
5. Keep investment themes in `investment-memo.md`, not in `macro-map.md`.

## Output

- `macro-map.md`
- Optional `market/shared-macro-data.json`
- Optional `market/shared-macro-view.md`

## Verification

- Confirm whether macro data was refreshed or deliberately reused, with the file date or `metadata.fetched_at`.
- Confirm each included macro item has source, latest read or trend, directional impact, transmission path, cadence, and thesis link.
- Confirm excluded variables have a reason.
- Confirm no trade instruction language was introduced.

## Red Lines

- Do not add macro data because it is popular.
- Do not use macro as a shortcut for valuation or thesis conclusions.
- Do not silently rely on stale shared macro data.
