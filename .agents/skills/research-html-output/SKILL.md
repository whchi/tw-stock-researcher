---
name: research-html-output
description: Use when the user asks to output a stock research synthesis, comprehensive result, summary, dashboard, or preview as HTML, or when the standard workflow finishes market-action-read.
---

# Research HTML Output

Use this for an explicit HTML output request, or when the standard workflow finishes `market-action-read` and needs the derived summary preview refreshed. Markdown and JSON case files remain the source of truth.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `docs/data-layout.md`, and `templates/research-html-summary.html`.
- Read the case Markdown and JSON artifacts; never treat the HTML preview as evidence.

## Workflow

1. Read the case files needed for the synthesis, especially `investment-memo.md`, `active-decisions.md`, `quality-and-valuation-check.md`, and `market-action-read.md`.
2. Build a JSON payload whose keys match placeholders in `templates/research-html-summary.html`.
3. Render with string replacement:

```bash
.venv/bin/python scripts/render_research_html.py \
  --data companies/<ticker-slug>/research-summary-data.json \
  --output companies/<ticker-slug>/research-summary.html
```

4. Keep the output in the company folder as `companies/<ticker-slug>/research-summary.html`.
5. Preserve disclaimer language and avoid buy/sell, entry/exit, stop-loss, or target-price wording.
6. Verify the rendered HTML exists and contains no unresolved `{{PLACEHOLDER}}` values.

## Payload Rules

- Values may contain HTML snippets such as `<tr>`, `<li>`, `<span class="tag good">`.
- Do not add new placeholders unless you update `templates/research-html-summary.html` and script tests.
- Use neutral research labels: `Verified Fact`, `Market Inference`, `Speculation To Verify`, `Scenario Analysis`.
- Explicitly set pricing-stage payload values from `investment-reasoning-framework.md` and `investment-memo.md`: `PRICING_STAGE_LABEL`, `PRICING_STAGE_READ`, and `PRICING_STAGE_ROWS`.
- `PRICING_STAGE_ROWS` must state whether the case is in Stage 1, Stage 2, Stage 3, or a transition state, and must include the evidence that would move it to the next stage.
- Include the egg-theory section when `market-action-read.md` or `market-data.json` has `derived.egg_theory_read`; preserve `snapshot_only` and holder-data-missing caveats.
- If `tdcc-data.json` is present, surface holder-distribution evidence as a research data point, not as a trade instruction.

## Verification

- Confirm `research-summary-data.json` is valid JSON.
- Confirm `research-summary.html` was written in the same company folder.
- Confirm no template placeholders remain unresolved.
- Confirm HTML remains a derived preview and does not replace source markdown files.

## Output

- `research-summary-data.json`
- `research-summary.html`
