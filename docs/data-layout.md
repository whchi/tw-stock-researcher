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
| `stock-meta.json` | current status, case file index, and workflow state (`stage_records`); each `file_references` value is `null` or a repo-relative case path | `stock-case-init` |
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
| `open-questions.md` | evidence-backed Active/Resolved question ledger; created by `stock-case-init`, then upserted/resolved only by the owning stage of each row's `question_namespace` via `scripts/open_questions.py` | `stock-case-init` (creation); `case-revisit` and `session-wrap` report on it but never write to it |
| `active-decisions.md` | current research stance, expected evidence timeline, thesis kill criteria, review triggers, and follow-ups | `session-wrap` |
| `research-summary-data.json` | typed, validated render payload built from the canonical case files above | `build_research_summary.py` |
| `research-summary.html` | deterministic HTML rendered from `research-summary-data.json` | `render_research_html.py` |

## Workflow State

`workflow-contract.json` at the repo root is the canonical stage DAG: dependencies, required/optional inputs, outputs, and question namespaces per stage. `scripts/workflow_state.py` reads it and tracks per-stage status inside each case's `stock-meta.json` under `stage_records`:

- `preflight`, `gate`, and `status` are read-only. `record` is the only command that writes `stock-meta.json`, and it does so atomically.
- Each stage record holds `status` (one of `workflow-contract.json`'s `stage_statuses`), `checked_at`, `source_as_of`, `input_hashes`, `output_hashes`, and `issues`. Hashes are keyed by case-relative filename, never absolute paths.
- `record` compares a stage's newly hashed outputs against its previously recorded outputs. If they differ, every transitive downstream consumer's stage record is marked `stale` — their artifacts are left untouched, but they must be re-run before a further downstream stage may consume them.
- `gate_stage` rejects a stage when any upstream dependency's last recorded status is not in `consumable_statuses` (`pass`/`degraded`), or when a required input file is missing or itself carries a non-consumable embedded `metadata.status`. Missing or degraded **optional** inputs never block readiness.
- A case is "complete" only when the terminal stage (`session-wrap`) has a stage record with a consumable status. A file existing on disk is not evidence that its producing stage passed — only a recorded stage status is.

## Research Summary Rendering

`templates/research-summary-data.schema.json` documents the typed payload shape; `scripts/research_summary_contract.py` enforces it in code (`validate_summary`, `canonical_json`) without adding a schema-validator runtime dependency.

- `scripts/build_research_summary.py` builds the payload from a fixed source map only (`stock-meta.json`, `active-decisions.md`, `investment-memo.md`, `market-data.json` + `tdcc-data.json`, validated `open-questions.md`, `DISCLAIMER.md`) and requires the `research-html-output` workflow gate to be ready first. It never reads an existing `research-summary-data.json` or `research-summary.html` as an input.
- `scripts/render_research_html.py` renders `research-summary.html` from that payload only, escaping every scalar with `html.escape(..., quote=True)` and accepting only `http`/`https` source URLs. Both scripts support `--check` to validate without writing, and both write atomically.
- `scripts/validate_research_summary.py --all` is a read-only audit of every existing case's current `research-summary-data.json`. Non-current or invalid shapes and source-manifest hash drift are invalid. Every manifest entry explicitly declares `root: case` or `root: repo`; both roots reject path escape.

## Validation Workflow

1. Run `sh tests/structure/test_templates.sh` after template or workflow-doc changes.
2. Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` after script or fetcher changes.
3. Add a focused structure test before changing file ownership, template boundaries, or workflow order.
4. `.github/workflows/verify.yml` runs steps 1-2 (structure checks plus the full unit-test suite) on every push and pull request, without touching `companies/**` or requiring `FIN_MIND_TOKEN`.

## Case Storage

See `docs/case-storage-policy.md` for the full policy on why `companies/**` is git-ignored, backup/export/retention guidance, and user-provided position-context handling.

Cases must use the current metadata, question-ledger, stage-record, and render-payload shapes. The repository provides no earlier-format migration path.
