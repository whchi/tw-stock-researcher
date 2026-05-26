# Data Layout

## Workspace Root

The root contains workflow docs, reusable templates, tests, and two top-level data areas: `market/` for shared context and `companies/` for per-stock cases.

## Shared Market Context

Use `market/shared-macro-view.md` and `market/shared-industry-view.md` only when the same context is reused across multiple cases. Create those files in `market/` by copying the corresponding templates from `templates/` when needed. Shared files should stay general and should not silently absorb company-specific thesis statements.

## Per-Stock Case Files

Create one folder per stock under `companies/`, for example `companies/6706-hui-te/`. A case should contain a copy of `stock-meta.json` plus the markdown files referenced from that metadata.

`file_references` uses one stable rule: each value is either `null` or one of the repo-relative paths rooted at the case directory under `companies/<ticker>-<company>/`. For example: `companies/6706-hui-te/company-analysis.md`.

## File Ownership

| File | Purpose | Primary owner |
| --- | --- | --- |
| `stock-meta.json` | current status and case file index; each `file_references` value is `null` or a repo-relative case path | `stock-case-init` |
| `yahoo-data.json` | Yahoo Finance Taiwan profile, revenue, income statement, cash flow, and derived summary for company deep-dive input | `fetch_yahoo.py` |
| `research-questions.md` | core questions and unknowns | `stock-case-init` |
| `company-analysis.md` | business facts, inference, and open questions | `company-deep-dive` |
| `industry-transmission.md` | transmission chain and indicators | `industry-transmission-analysis` |
| `macro-map.md` | included and excluded macro variables | `macro-impact-analysis` |
| `quality-and-valuation-check.md` | value-investor quality layer: ROIC, owner earnings, working-capital quality, capital allocation, implied expectations, and margin of safety | `quality-and-valuation-check` |
| `investment-memo.md` | current thesis memo | `investment-thesis` |
| `market-data.json` | FinMind price, volume, and institutional investor data; raw rows plus derived 1D/3D/5D windows | `fetch_finmind.py` |
| `market-action-read.md` | neutral market-state read using price/volume and institutional flow evidence, without trading instructions | `market-action-read` |
| `signal-log.md` | append-only event log with signal classification | `signal-update` |
| `thesis-updates.md` | explicit thesis changes | `signal-update` |
| `open-questions.md` | unresolved questions to carry forward | `case-revisit`, `session-wrap` |
| `active-decisions.md` | current research stance, expected evidence timeline, thesis kill criteria, review triggers, and follow-ups | `session-wrap` |

## Validation Workflow

1. Run `sh tests/structure/test_templates.sh` after template or workflow-doc changes.
2. Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` after script or fetcher changes.
3. Add a focused structure test before changing file ownership, template boundaries, or workflow order.
