---
name: investment-thesis
description: Use when writing or refreshing investment-memo.md with Bull/Base/Bear scenarios, business thesis, pricing thesis, and expectation-gap analysis.
---

# Investment Thesis

Synthesize the case without collapsing evidence, judgment, and market pricing into one blob.

## Source Of Truth

- Follow `AGENTS.md`, `DISCLAIMER.md`, `templates/investment-memo.md`, and `investment-reasoning-framework.md`.
- Read `quality-and-valuation-check.md` before writing the memo.

## Workflow

1. Read the current company, financial, industry, macro, and quality layers.
2. Write the dual framework: Business Thesis and Pricing Thesis.
3. Build a cross-layer conflict map across business, financial, industry, macro, quality / valuation, and market-action evidence. Preserve every material disagreement, identify the time horizon behind each signal, state only sourced reconciliations, name the evidence that would resolve the conflict, and apply the result to confidence.
4. Run the adversarial review before assigning Bull/Base/Bear probabilities. The Bull Researcher states the strongest supported positive case, the Bear Researcher states the strongest counterevidence and failure conditions, and the Risk Reviewer audits data dates, missing inputs, causal leaps, conflicting definitions, and valuation assumptions. All three reviewers must use the same evidence cutoff.
5. Apply the Stage 1 → Stage 2 verification gate from `investment-reasoning-framework.md`: assess structure, quality, and narrative separately from sourced evidence; do not infer a passed gate from price action alone.
6. Include Bull/Base/Bear scenarios with probability weights, EPS or driver assumptions, and scenario-derived price ranges; anchor scenario multiples to the `fundamentals-data.json` valuation band rather than remembered multiples. Assign the weights only after recording how the adversarial review changed them.
7. Explain expectation gaps: market belief, verified evidence, narrative-only claims, and verification needed.
8. Identify an information edge only when a sourced, decision-relevant observation is plausibly underemphasized by the current market narrative; otherwise state that no defensible edge was identified.
9. Calibrate each required evidence layer as High, Medium, or Low confidence. Any Low layer must automatically lower overall memo confidence to no higher than Medium; two or more Low layers, or one missing load-bearing input, lower it to Low.
10. Summarize every decision-relevant update with the `Evidence → Thesis Impact → Next Verification` contract. State separately whether it affects the Business Thesis, Pricing Thesis, or both, and include the observation date and source.
11. Capture critical unresolved questions and non-portable claims.

## Output

- `investment-memo.md`
- Optional updates to `open-questions.md`

## Verification

- Confirm every scenario-derived range is tied to explicit assumptions.
- Confirm the Pricing Stage Verification records evidence and a result for structure, quality, and narrative; any missing input remains `Insufficient data`.
- Confirm every claimed information edge cites the observation, source, why it may be overlooked, and counterevidence; otherwise use the explicit no-edge result.
- Confirm the cross-layer conflict map covers every material disagreement, preserves different time horizons, identifies resolution evidence, and changes confidence when the conflict remains unresolved.
- Confirm the Bull Researcher, Bear Researcher, and Risk Reviewer each record their strongest evidence, counterevidence, failure condition, and effect on scenario weights before probabilities are assigned.
- Confirm every recent evidence conclusion follows `Evidence → Thesis Impact → Next Verification` and names its source and observation date.
- Confirm low-confidence evidence layers automatically lower overall memo confidence under the stated rule.
- Confirm scenario multiple assumptions cite valuation-band context when `fundamentals-data.json` provides it.
- Confirm the memo does not duplicate full financial, macro, quality, or market-action tables.
- Confirm disclaimer language and no-advice wording are present.

## Red Lines

- Do not write unsupported price targets.
- Do not use imperative recommendation language.
- Do not treat narrative expansion as fundamental validation.
