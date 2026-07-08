---
name: quality-and-valuation-check
description: Use when assessing business quality, owner earnings, capital allocation, implied expectations, and margin-of-safety evidence before the investment memo.
---

# Quality And Valuation Check

Write the judgment layer that sits between financial facts and the investment memo.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/quality-and-valuation-check.md`.
- Read `financial-analysis.md` before writing this file.
- Valuation multiples come from `fundamentals-data.json` → `derived.valuation_band`.

## Workflow

1. Start from verified financial facts and coverage limitations.
2. Assess business quality using ROIC, owner earnings, cash conversion, working-capital quality, and capex productivity.
3. Evaluate capital allocation and shareholder value accrual.
4. Separate current price implied expectations from verified evidence, anchoring P/E and P/B reads to `derived.valuation_band` (current value vs 1y/3y/5y min / median / max and percentile) instead of remembered multiples.
5. Frame margin of safety as scenario evidence and assumption sensitivity, not as an instruction.
6. List better-source checks where public data is insufficient.

## Output

- `quality-and-valuation-check.md`
- Optional updates to `open-questions.md`

## Verification

- Confirm the analysis references financial facts rather than repeating raw tables.
- Confirm implied expectations are clearly separated from verified evidence.
- Confirm the valuation-band table cites `fundamentals-data.json` or explicitly notes the band is missing.
- Confirm no unsupported price target or direct recommendation language was introduced.

## Red Lines

- Do not write this layer before reading `financial-analysis.md`.
- Do not quote historical or peer multiples from memory when `valuation_band` data exists.
- Do not turn a scenario range into a target price.
- Do not hide low-confidence assumptions.
