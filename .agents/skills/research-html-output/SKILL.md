---
name: research-html-output
description: Use when the user asks to output a stock research synthesis, comprehensive result, summary, dashboard, or preview as HTML.
---

# Research HTML Output

Use this only for an explicit HTML output request. Markdown and JSON case files remain the source of truth.

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

## Payload Rules

- Values may contain HTML snippets such as `<tr>`, `<li>`, `<span class="tag good">`.
- Do not add new placeholders unless you update `templates/research-html-summary.html` and script tests.
- Use neutral research labels: `Verified Fact`, `Market Inference`, `Speculation To Verify`, `Scenario Analysis`.
- Include the egg-theory section when `market-action-read.md` or `market-data.json` has `derived.egg_theory_read`; preserve `snapshot_only` and holder-data-missing caveats.
- If `tdcc-data.json` is present, surface holder-distribution evidence as a research data point, not as a trade instruction.
