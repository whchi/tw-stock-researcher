---
name: quality-and-valuation-check
description: Use when assessing business quality, owner earnings, capital allocation, implied expectations, and margin-of-safety evidence before the investment memo.
---

# Quality And Valuation Check

Write the judgment layer that sits between financial facts and the investment memo.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/quality-and-valuation-check.md`.
- Read `financial-analysis.md` before writing this file.
- Use `fundamentals-data.json` → `derived.valuation_band` as historical context, not an automatic selection rule for multiples.

## Workflow

1. Start from verified financial facts and coverage limitations.
2. Assess business quality using ROIC, owner earnings, cash conversion, working-capital quality, and capex productivity.
3. Evaluate capital allocation and shareholder value accrual.
4. Build the operating assumptions bridge: revenue volume / price / mix, margins and costs, tax and diluted shares, working capital, capex and cash flow. Cite inputs, period, units and gaps; choose a valuation method suited to the business.
5. Separate conditional price-implied assumptions from observed expectations. A current price / trailing P/E calculation only reproduces trailing EPS. State fixed inputs, solved variable, valuation date, target period, accounting basis, timing and discounting where applicable; present multiple combinations and sensitivity of at least two material inputs. Block calculations whose load-bearing inputs are unavailable.
6. Own the Bull/Base/Bear scenario calculations and ranges here; the memo cites them rather than making an independent set. Use the valuation band as historical context, explain comparability and multiple choice, and distinguish unsupported expectations from sourced forecasts.
7. Frame margin of safety as scenario evidence and assumption sensitivity, not as an instruction. List better-source checks where public data is insufficient.

## Output

- `quality-and-valuation-check.md`
- Optional updates to `open-questions.md`

## Verification

- Confirm the analysis references financial facts rather than repeating raw tables.
- Confirm implied expectations are clearly separated from verified evidence.
- Confirm the bridge connects operating drivers to earnings and cash, and conditional reverse valuation records fixed assumptions, timing, sensitivity and missing inputs.
- Confirm memo ranges cite this layer's calculations or are explicitly blocked.
- Confirm the valuation-band table cites `fundamentals-data.json` or explicitly notes the band is missing.
- Confirm no unsupported price target or direct recommendation language was introduced.

## Red Lines

- Do not write this layer before reading `financial-analysis.md`.
- Do not quote historical or peer multiples from memory when `valuation_band` data exists.
- Do not turn a scenario range into a target price.
- Do not hide low-confidence assumptions.
