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
| `raw-data.json` | Goodinfo annual statements and coverage checks | `fetch_goodinfo.py` |
| `fundamentals-data.json` | FinMind official monthly revenue, quarterly IS / BS / CF, and P/E / P/B valuation band with derived 6M / 8Q reads | `fetch_fundamentals.py` |
| `research-questions.md` | core questions and unknowns | `stock-case-init` |
| `company-analysis.md` | business facts, inference, and open questions | `company-deep-dive` |
| `financial-analysis.md` | annual and quarterly operating, profitability, and financial-health fact layer | `financial-analysis` |
| `industry-transmission.md` | transmission chain and indicators | `industry-transmission-analysis` |
| `macro-map.md` | included and excluded macro variables | `macro-impact-analysis` |
| `quality-and-valuation-check.md` | value-investor quality layer: ROIC, owner earnings, working-capital quality, capital allocation, implied expectations, and margin of safety | `quality-and-valuation-check` |
| `investment-memo.md` | current thesis memo | `investment-thesis` |
| `market-data.json` | FinMind price, volume, institutional, margin, shareholding, and day-trading data; raw rows plus derived 1D/3D/5D windows and 1m/3m/6m egg-theory reads | `fetch_finmind.py` |
| `tdcc-data.json` | TDCC ownership distribution: latest snapshot plus accumulated weekly `history` for holder-count trends | `fetch_tdcc.py` |
| `market-action-read.md` | neutral market-state read using price/volume and institutional flow evidence, without trading instructions | `market-action-read` |
| `research-summary-data.json` | derived payload for the HTML preview | `research-html-output` |
| `research-summary.html` | derived HTML preview; never a source of truth | `research-html-output` |
| `signal-log.md` | append-only event log with signal classification | `signal-update` |
| `thesis-updates.md` | explicit thesis changes | `signal-update` |
| `open-questions.md` | unresolved questions to carry forward | `case-revisit`, `session-wrap` |
| `active-decisions.md` | current research stance, expected evidence timeline, thesis kill criteria, review triggers, and follow-ups | `session-wrap` |

## Current Data Availability Contract

Every generated source JSON must include `metadata.fetched_at` and
`metadata.data_availability` with exactly these required fields:

| Field | Meaning |
|---|---|
| `status` | `available`, `partial`, or `unavailable` for the current run |
| `observation_date` | Latest actual source observation or reporting period; never the fetch timestamp |
| `source` | Source that produced the current artifact |
| `missing_inputs` | Required datasets or fields absent from the current result |
| `failure_reasons` | Provider, permission, endpoint, parsing, or empty-response failures from the current run |
| `confidence_impact` | `none`, `downgrade`, or `block` |

`partial` requires explicit confidence reduction. `unavailable` blocks the
dependent evidence layer. A provider failure is not a negative company signal.
Current workflow runs do not accept legacy availability shapes or inferred
defaults.

## Validation Workflow

1. Run `sh tests/structure/test_templates.sh` after template or workflow-doc changes.
2. Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` after script or fetcher changes.
3. Add a focused structure test before changing file ownership, template boundaries, or workflow order.

The `Primary owner` may create or refresh its artifact. Other skills may only make the narrow cross-layer updates explicitly listed in `AGENTS.md`; they must not rewrite another layer wholesale. Deleting history or replacing user-authored narrative content still requires explicit approval.
