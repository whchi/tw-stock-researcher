---
name: research-html-output
description: Use when the user asks to output a stock research synthesis, comprehensive result, summary, dashboard, or preview as HTML.
---

# Research HTML Output

Use this only for an explicit HTML output request. Markdown and JSON case files remain the source of truth. This stage requires a passing `session-wrap` gate — HTML is never built from an incomplete or stale case. The payload is built deterministically by `scripts/build_research_summary.py` from fixed source files; do not hand-write `research-summary-data.json`.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/research-summary-data.schema.json` (the payload shape; enforced in code by `scripts/research_summary_contract.py`).
- The fixed source map: identity from `stock-meta.json`; headline/summary/stance/KPIs/evidence timeline/kill criteria/watch items from `active-decisions.md`; expectation gaps/pricing stage/scenarios from `investment-memo.md`; egg theory from `market-data.json` (`derived.egg_theory_read`) with a TDCC caveat from `tdcc-data.json`; open questions from validated `open-questions.md`; disclaimer text from `DISCLAIMER.md`. Never consult an existing `research-summary-data.json` or `research-summary.html` as a builder input.

## Commands

```bash
.venv/bin/python scripts/build_research_summary.py --case companies/<ticker-slug>
.venv/bin/python scripts/build_research_summary.py --case companies/<ticker-slug> --check
.venv/bin/python scripts/render_research_html.py --case companies/<ticker-slug>
.venv/bin/python scripts/render_research_html.py --case companies/<ticker-slug> --check
```

`--check` validates without writing. `--distribution shareable` on the builder rejects any source flagged `restricted` (e.g. non-official/secondary-aggregator data) instead of silently including it.

## Workflow

1. Preflight: `.venv/bin/python scripts/workflow_state.py gate <case_dir> research-html-output --as-of <YYYY-MM-DD> --json`; if `ready` is false (most commonly because `session-wrap` has not passed, or a required input like `market-action-read.md` is missing), run or finish the listed upstream stage first instead of rendering from stale evidence.
2. Run `build_research_summary.py --case <case_dir>` to produce a fresh, validated `research-summary-data.json`. It fails closed (non-zero exit, nothing written) on a missing required source, a malformed table, an invalid payload shape, or a stage that is not actually gate-ready.
3. Run `render_research_html.py --case <case_dir>` to render `research-summary.html` from that payload. Every value is HTML-escaped; the renderer never trusts pre-formatted HTML from a case file.
4. Record: `.venv/bin/python scripts/workflow_state.py record <case_dir> research-html-output`.
5. Track unresolved rendering gaps under question namespace `HTML` only via `scripts/open_questions.py upsert <case_dir> --stage research-html-output --id HTML-<slug> ...`.

## Verification

- Confirm `research-summary-data.json` and `research-summary.html` (i.e. `companies/<ticker-slug>/research-summary.html`) were both written in the same company folder.
- Confirm re-running both commands on unchanged source files produces byte-identical output (determinism).
- Confirm the HTML's `Build Provenance` section shows the current `schema_version`/`template_version` and a `source_manifest` entry per consulted file.
- Confirm HTML remains a derived preview and does not replace source markdown files.

## Red Lines

- Do not hand-construct `research-summary-data.json`; always go through `build_research_summary.py` so the payload stays typed and validated.
- Do not add new template placeholders unless you also add a builder field, a `render_*` function, and a schema entry.
- Do not include restricted (non-official) sources when the user asked for a shareable/exportable render.
