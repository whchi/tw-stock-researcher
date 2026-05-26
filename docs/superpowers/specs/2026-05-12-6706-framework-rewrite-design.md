# 6706 Framework Rewrite Design

## Goal

Bring `companies/6706-whit/investment-memo.md` and its dependent case files up to full compliance with `investment-reasoning-framework.md`, with explicit 6M evidence mapping, pricing-stage judgment, scenario linkage, and neutral research wording.

## Scope

- In scope:
  - `companies/6706-whit/investment-memo.md`
  - `companies/6706-whit/active-decisions.md`
  - `companies/6706-whit/open-questions.md`
  - `companies/6706-whit/signal-log.md`
  - supporting design and implementation docs under `docs/superpowers/`
- Out of scope:
  - backfilling `2344-winbond` and `6451-shunsin-ky`
  - changing scripts, templates, or shared docs
  - adding new market-data fetch logic

## Current Gap

The current `6706` memo already contains the dual-framework skeleton, but it does not fully execute the framework's mandatory decision flow.

Missing or incomplete items:

1. Explicit 6M price-path evidence and revenue-path linkage.
2. Historical valuation band comparison and peer valuation comparison inside the Pricing Thesis.
3. Clear distinction between verified facts and narrative amplifiers in the recent-event layer.
4. Explicit pricing-stage judgment with rationale.
5. Market-regime linkage back to the case stance.
6. Scenario sections that each state:
   - assumptions
   - probability weight
   - scenario-derived price range
   - structure-break condition
   - validation trigger
   - whether the recent 6M evidence supports or does not support that scenario

## Evidence Base

The rewrite will rely only on already collected or freshly re-fetched public data already aligned with the case:

- 6M price path from FinMind `TaiwanStockPrice`:
  - first close: `2025-11-03` `69.2`
  - low close: `2025-11-04` `66.1`
  - high close: `2026-05-05` `183.0`
  - last close: `2026-05-11` `168.5`
  - 6M change: `+143.50%`
  - rebound low to last: `+154.92%`
  - rebound low to high: `+176.85%`
  - drawdown high to last: `-7.92%`
- 6M valuation path from FinMind `TaiwanStockPER`:
  - current `PBR 3.45`
  - 6M min `PBR 1.36` on `2025-11-04`
  - 6M max `PBR 3.75` on `2026-05-05`
  - `PER` is not usable because recent rows remain `0`
- Peer valuation snapshots on `2026-05-11`:
  - `4977` `PBR 4.89`, `PER 55.66`
  - `4576` `PBR 7.25`, `PER 98.62`
  - `5536` `PBR 8.47`, `PER 31.53`
  - `3593` `PBR 3.88`, `PER 0`
- Existing 7M revenue path already captured in the case:
  - `2025/10 -> 2026/04`: `0.37 -> 0.41 -> 0.43 -> 0.50 -> 0.54 -> 0.55 -> 0.54` 億
  - `2026/04`: `MoM -2.71%`, `YoY -41.83%`

## Recommended Approach

Use a surgical rewrite rather than a full case rebuild.

Reasons:

1. The case already has valid business-thesis and financial-stress content.
2. The missing work is structural and evidentiary, not conceptual.
3. Keeping the change focused reduces risk of accidentally rewriting good research into weaker or less precise language.

## Planned Document Structure

### `investment-memo.md`

Reorder and expand the memo into this sequence:

1. Disclaimer and framework reference
2. Current view
3. Dual framework
   - Business Thesis
   - Pricing Thesis
4. Recent 6M Evidence Layer
   - monthly revenue path
   - price path
   - event and narrative audit
   - price vs revenue / EPS divergence
5. Stage judgment
6. Market regime linkage
7. Checklist read
8. Scenario analysis
   - Bull
   - Base
   - Bear
   - each with evidence support, validation trigger, and structure-break condition
9. Monitoring and unresolved question
10. Sources

### `active-decisions.md`

Tighten the live stance so it reflects:

- current stage as late Stage 1 / not yet Stage 2
- current P/B being near the upper end of the 6M band
- explicit observation ranges tied to validation and structure-break logic

### `open-questions.md`

Keep unresolved items focused on:

- new-product revenue contribution
- CAPEX purpose and return path
- whether near-top-band valuation can hold without EPS follow-through

### `signal-log.md`

Append a new dated entry logging that the framework rewrite changed the read from generic "turnaround validation" to a more explicit "late Stage 1 / valuation already pulled forward" framing.

## Risks And Guardrails

- No fabricated broker target-price or media-call evidence. If not verifiable, state that the repo currently lacks direct captured evidence.
- No imperative recommendation language.
- All valuation output remains `scenario-derived price range` tied to assumptions.
- If evidence is mixed, say so directly instead of forcing a stronger conclusion.

## Success Criteria

The rewrite is complete when:

1. `investment-memo.md` explicitly covers every mandatory framework section.
2. Each scenario contains assumptions, probability, price range, validation trigger, structure-break condition, and 6M evidence support status.
3. Dependent files reflect the same live stance and validation logic.
4. A compliance sweep finds no recommendation or target-price language.
