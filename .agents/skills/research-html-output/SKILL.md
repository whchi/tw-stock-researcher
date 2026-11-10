---
name: research-html-output
description: Use when the user asks for an HTML research summary or when the standard workflow finishes session-wrap.
---

# Research HTML Output

Use this for an explicit HTML output request, or when the standard workflow finishes `session-wrap` and needs the derived summary preview refreshed. Markdown and JSON case files remain the source of truth.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `docs/data-layout.md`, and `templates/research-html-summary.html`.
- Read the case Markdown and JSON artifacts; never treat the HTML preview as evidence.

## Workflow

1. After `session-wrap`, read the completed current case files needed for the synthesis, especially `investment-memo.md`, `active-decisions.md`, `quality-and-valuation-check.md`, and `market-action-read.md`. Never use a stale predecessor when a refresh failed. A current-schema `unavailable` artifact may be shown as unavailable with its dependent conclusions blocked; if a required current artifact or contract block is absent, report the blocker and do not render.
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
- `PRICING_STAGE_ROWS` must state Stage 1, Stage 2, Stage 3, a transition state, or `Insufficient data`, and include the evidence needed for the next assessment.
- Build `PRICING_STAGE_GATE_ROWS` from `investment-memo.md` → `Pricing Stage Verification`. Emit one row each for Structure, Quality, and Narrative with current evidence, `Confirmed` / `Not confirmed` / `Insufficient data`, and the missing evidence or next check.
- Build `CONFIDENCE_CALIBRATION_ROWS` from `investment-memo.md` → `Confidence Calibration`. Emit one row per evidence layer with High / Medium / Low confidence, the reason, and missing or conflicting evidence; preserve the memo's automatic confidence-downgrade rule.
- Build `CROSS_LAYER_CONFLICT_ROWS` from `investment-memo.md` → `Cross-Layer Conflict Map`. Preserve time horizons and unresolved disagreements; do not collapse the rows into a single direction.
- Build `ADVERSARIAL_REVIEW_ROWS` from `investment-memo.md` → `Adversarial Review`. Emit one row each for Bull Researcher, Bear Researcher, and Risk Reviewer, including the recorded effect on scenario weights.
- Build `EVIDENCE_THESIS_VERIFICATION_ROWS` from `investment-memo.md` → `Recent Evidence Conclusion` and `active-decisions.md` → `Evidence → Thesis Impact → Next Verification`. Every row must identify the source / observation date and whether it affects the Business Thesis, Pricing Thesis, or both.
- Build `DATA_AVAILABILITY_ROWS` from the current `metadata.data_availability` object in every required source JSON. Emit artifact, status, observation date, source, missing inputs / failure reasons, and confidence impact. `unavailable` must block conclusions from that evidence layer; provider failure is not a negative company signal.
- Every template placeholder is required in the current payload. Do not synthesize placeholder defaults or accept an incomplete payload.
- Include the egg-theory section when `market-action-read.md` or `market-data.json` has `derived.egg_theory_read`; preserve `snapshot_only` and holder-data-missing caveats.
- If `tdcc-data.json` is present, surface holder-distribution evidence as a research data point, not as a trade instruction.

## Verification

- Confirm `research-summary-data.json` is valid JSON.
- Confirm Pricing Stage Verification contains Structure, Quality, and Narrative rows.
- Confirm Confidence Calibration lists each required evidence layer.
- Confirm Cross-Layer Conflict Map, Adversarial Review, Evidence → Thesis Impact → Next Verification, and Data Availability are present and populated from current source files.
- Confirm every required source JSON has `metadata.data_availability`; do not render when a required contract block is missing.
- Confirm `research-summary.html` was written in the same company folder.
- Confirm no template placeholders remain unresolved.
- Confirm HTML remains a derived preview and does not replace source markdown files.

## Output

- `research-summary-data.json`
- `research-summary.html`
