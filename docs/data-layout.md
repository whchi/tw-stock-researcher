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
| `official-issuer-data.json` | TWSE/TPEx official issuer, monthly revenue, and IS/BS summary data | `fetch_official_issuer.py` |
| `raw-data.json` | Goodinfo scraped annual statements plus three-statement coverage check | `fetch_goodinfo.py` |
| `fundamentals-data.json` | FinMind official monthly revenue, quarterly IS / BS / CF, and P/E / P/B valuation band with derived 6M / 8Q reads | `fetch_fundamentals.py` |
| `research-questions.md` | core questions and unknowns | `stock-case-init` |
| `company-analysis.md` | business facts, inference, and open questions | `company-deep-dive` |
| `financial-analysis.md` | financial fact layer: operating, profitability, and balance-sheet analysis; a pure consumer of `financial-data-fetch`'s output | `financial-analysis` |
| `industry-transmission.md` | transmission chain and indicators | `industry-transmission-analysis` |
| `macro-map.md` | included and excluded macro variables | `macro-impact-analysis` |
| `quality-and-valuation-check.md` | value-investor quality layer: ROIC, owner earnings, working-capital quality, capital allocation, implied expectations, and margin of safety | `quality-and-valuation-check` |
| `investment-memo.md` | current thesis memo | `investment-thesis` |
| `market-data.json` | FinMind price, volume, institutional, margin, shareholding, and day-trading data; raw rows plus derived 1D/3D/5D windows and 1m/3m/6m egg-theory reads | `fetch_finmind.py` |
| `tdcc-data.json` | TDCC ownership distribution: latest snapshot plus accumulated weekly `history` for holder-count trends | `fetch_tdcc.py` |
| `market-action-read.md` | neutral market-state read using price/volume and institutional flow evidence, without trading instructions | `market-action-read` |
| `signal-log.md` | append-only event log with signal classification | `signal-update` |
| `thesis-updates.md` | explicit thesis changes | `signal-update` |
| `open-questions.md` | Active/Resolved question ledger carried across sessions; created by `stock-case-init`, updated by the analysis stages | `stock-case-init` (creation); analysis stages add and resolve their own items |
| `active-decisions.md` | current research stance, expected evidence timeline, thesis kill criteria, review triggers, and follow-ups | `session-wrap` |
| `research-summary-data.json` | typed, validated render payload built from the canonical case files above | `build_research_summary.py` |
| `research-summary.html` | deterministic HTML rendered from `research-summary-data.json` | `render_research_html.py` |

## Research Summary Rendering

`templates/research-summary-data.schema.json` documents the typed payload shape; `scripts/research_summary_contract.py` enforces it in code (`validate_summary`, `canonical_json`) without adding a schema-validator runtime dependency.

- `scripts/build_research_summary.py` builds the payload from a fixed source map only (`stock-meta.json`, `active-decisions.md`, `investment-memo.md`, `market-data.json` + `tdcc-data.json`, `open-questions.md`, `DISCLAIMER.md`). It never reads an existing `research-summary-data.json` or `research-summary.html` as an input. Section extraction is tolerant — headings are matched by containment against the `templates/` shapes with common column aliases, and a missing section renders as an empty block; the build fails only on a missing source file or an invalid payload.
- `scripts/render_research_html.py` renders `research-summary.html` from that payload only, escaping every scalar with `html.escape(..., quote=True)` and accepting only `http`/`https` source URLs. Both scripts support `--check` to validate without writing, and both write atomically.
- `scripts/validate_research_summary.py --all` is a read-only audit of every existing case's current `research-summary-data.json`. Non-current or invalid shapes and source-manifest hash drift are invalid. Every manifest entry explicitly declares `root: case` or `root: repo`; both roots reject path escape.

## Validation Workflow

1. Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` after changing the HTML render pipeline.
2. `.github/workflows/verify.yml` runs the same suite on every push and pull request, without touching `companies/**` or requiring `FIN_MIND_TOKEN`.

## Case Storage

See `docs/case-storage-policy.md` for the full policy on why `companies/**` is git-ignored, backup/export/retention guidance, and user-provided position-context handling.

Cases must use the current metadata, question-ledger, stage-record, and render-payload shapes. The repository provides no earlier-format migration path.
