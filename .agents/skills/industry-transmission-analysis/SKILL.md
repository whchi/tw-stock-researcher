---
name: industry-transmission-analysis
description: Use when mapping a stock's industry chain, demand transmission, leading indicators, and noise-versus-signal checks.
---

# Industry Transmission Analysis

Explain how industry demand becomes company revenue, margin, cash flow, and narrative pressure.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/industry-transmission.md`.
- Use `company-analysis.md`, verified filings, public industry sources, and reusable `market/shared-industry-view.md` only when it is genuinely shared context.

## Workflow

1. Identify the company's position in the value chain.
2. Map upstream inputs, customers, channel inventory, end-demand drivers, and cycle risks.
3. Separate leading indicators from lagging indicators and popular but weak signals.
4. Link each indicator to the specific company-level transmission path.
5. Record unresolved industry evidence in `open-questions.md`.

## Output

- `industry-transmission.md`
- Optional `market/shared-industry-view.md` when the context is reusable across cases

## Verification

- Confirm every included indicator has a company-specific transmission path.
- Confirm the file does not merely restate a broad theme.
- Confirm no trade instruction language was introduced.

## Red Lines

- Do not let theme popularity substitute for evidence.
- Do not mix company-specific thesis claims into shared market files.
- Do not treat one article or report as consensus unless verified.
