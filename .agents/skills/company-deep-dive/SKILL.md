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

1. Confirm `yahoo-data.json` exists; if missing, run `yahoo-profile-financials` first.
2. Read `stock-meta.json`, `research-questions.md`, and `yahoo-data.json`.
3. Separate verified facts, management claims, market inference, and speculation to verify.
4. Cover business model, product mix, technical bottleneck, customer dependency, switching cost, monetization path, and margin drivers.
5. Keep unresolved items in `open-questions.md` when they affect the thesis but are not verifiable yet.

## Output

- `company-analysis.md`

## Verification

- Confirm material claims have a source or are labeled as inference/speculation.
- Confirm the writeup distinguishes current revenue contribution from future narrative.
- Confirm no direct trade instruction language was introduced.

## Red Lines

- Do not present market narratives as verified demand.
- Do not use paid-source claims unless the user provided the source.
- Do not duplicate full financial tables that belong in `financial-analysis.md`.
