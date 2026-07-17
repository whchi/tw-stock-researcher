---
name: company-deep-dive
description: Use when writing or refreshing company-analysis.md for a stock case after profile and business facts are available.
---

# Company Deep Dive

Write the business fact layer: what the company sells, who pays, why it matters, and what must be verified.

## Source Of Truth

- Follow `AGENTS.md`, `docs/data-layout.md`, and `templates/company-analysis.md`.
- Prefer `yahoo-data.json`, company filings, MOPS, company website, and source-labeled public reports.

## Workflow

1. Read `stock-meta.json`, `research-questions.md`, and `yahoo-data.json` if available.
2. Separate verified facts, management claims, market inference, and speculation to verify.
3. Cover business model, product mix, technical bottleneck, customer dependency, switching cost, monetization path, and margin drivers.
4. Run segment transition analysis only when segment definitions and revenue shares are comparable. Flag a major structural shift when any segment changes by at least 15 percentage points over two comparable fiscal years or a new segment appears; use disclosed segment margins to classify upgrading / downgrading / stable / diversifying.
5. Keep the major-shift flag separate from the Pricing Stage gate: the former uses a 15-point materiality threshold, while `investment-reasoning-framework.md` uses a 5-point higher-margin-share threshold for Stage 1 → Stage 2 verification.
6. If segment definitions changed, segment margins are unavailable, or only company-wide margin exists, write `Insufficient data`; do not substitute consolidated gross margin for segment margin.
7. Add management narrative tracking when comparable annual reports, MOPS operating reports, company announcements, or investor presentations are available: map prior commitments to current-period outcomes, distinguish plan language from outcome language, and flag previously emphasized topics that are now silent.
8. If comparable management text is unavailable, write `Insufficient data`; treat silence as an open question rather than evidence that a commitment was abandoned or failed.
9. Keep unresolved items in `open-questions.md` when they affect the thesis but are not verifiable yet.

## Output

- `company-analysis.md`
- Optional updates to `open-questions.md`

## Verification

- Confirm material claims have a source or are labeled as inference/speculation.
- Confirm the writeup distinguishes current revenue contribution from future narrative.
- Confirm segment comparisons use stable definitions and disclosed segment-level margin evidence; otherwise classify the transition as `Insufficient data`.
- Confirm every management-commitment status cites both the prior statement and current-period evidence, or is labeled `Insufficient data`.
- Confirm no direct trade instruction language was introduced.

## Red Lines

- Do not present market narratives as verified demand.
- Do not use paid-source claims unless the user provided the source.
- Do not duplicate full financial tables that belong in `financial-analysis.md`.
