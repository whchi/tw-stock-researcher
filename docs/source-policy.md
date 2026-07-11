# Source Policy

This document defines the source hierarchy, the provenance fields every
official adapter must carry, and how conflicting values across sources are
classified. It is written before repositioning any existing fetcher's
priority (Task 8 Step 1), and the live findings below were verified by
actually calling each endpoint with strict TLS verification — not assumed.

## Source Tiers

| Tier | Sources | Role |
| --- | --- | --- |
| `official` | TWSE OpenAPI (`openapi.twse.com.tw`), TDCC OpenAPI (`openapi.tdcc.com.tw`) | Canonical when period/unit/currency/consolidation/restatement match |
| `official_unverified` | TPEx OpenAPI (`www.tpex.org.tw/openapi`) | Same tier by design, but currently unreachable under strict TLS verification — see below |
| `secondary_aggregator` | FinMind | Normalized history/cache; reconciled against `official` before being treated as canonical |
| `unofficial_scrape` | Goodinfo.tw | Temporary annual fallback / sanity check only |
| `unofficial_secondary` | Yahoo Finance Taiwan | Local profile/discovery fallback; excluded from shareable render payloads |

## Verified Endpoint Findings (2026-07-11)

Each endpoint below was called directly (via Python's `requests`, the same
library the fetchers use) with default strict certificate verification —
no `verify=False`, no bypass. Results are facts, not assumptions:

| Endpoint | Result |
| --- | --- |
| `https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK` | **OK** — strict TLS succeeds with `requests`' bundled CA store |
| `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` (company basic info) | **OK** |
| `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` (monthly revenue) | **OK** |
| `https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci` / `t187ap07_L_ci` (general-industry income statement / balance sheet) | **OK; required for a general issuer** |
| `t187ap06/07_{L,O}_{basi,bd,fh,ins}` (financial-industry income statement / balance sheet variants) | **Required for a financial issuer; search the allowlisted variants and retain the one matching the company code** |
| `t187ap04/02/11/09/12/45_{L,O}` (material events, >10% shareholders, director holdings/pledges, insider transfer declarations, dividends) | **Contextual official evidence; zero matched rows is a valid no-event/no-disclosure result, while endpoint failure is recorded as a source error** |
| `https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O` (TPEx company basic info) | **FAILS** — `SSLError: CERTIFICATE_VERIFY_FAILED: Missing Subject Key Identifier`, confirmed with both Python's raw `ssl` module and `requests`/certifi |
| `https://openapi.tdcc.com.tw/v1/opendata/1-5` (TDCC ownership distribution) | **OK** — native JSON response and valid certificate |

**Consequence:** the official TWSE and TDCC adapters can
both run under strict TLS verification with no workaround. The TPEx
adapter's certificate genuinely fails verification today. Per this policy's
own rule (next section), that is treated as **a source failure, not a
reason to disable verification** — `fetch_official_issuer("...", market="TPEx", ...)`
fails closed (`blocked`) until TPEx fixes their certificate chain. This is
an external dependency outside this repository's control; re-verify
periodically rather than assuming it is permanent.

## Required Provenance Fields

Every official-adapter record must carry:

- `endpoint`: the exact URL called (from a fixed allowlist; never string-built from untrusted input beyond the stock id).
- `dataset_id`: the source's own dataset code (e.g. `t187ap05_L`, `1-5`).
- `as_of` / `period_type` / `period_key`: when the value applies, in the source's own period vocabulary (`monthly`, `quarterly`, `snapshot`) — see `normalize_period` in `scripts/fetch_official_issuer.py`.
- `unit` / `currency`: e.g. `TWD_thousand`, `TWD`.
- `consolidation`: `consolidated` or `individual` (parent-only) scope.
- `audit_status` / `restated`: whether the figure is auditor-reviewed and whether it restates a prior filing.
- `license_id`: the dataset's stated redistribution terms (`data.gov.tw` open license references where published).
- `distribution_scope`: whether the record may appear in a `shareable` render payload.
- `raw_hash`: SHA-256 of the raw response bytes actually stored.
- `parser_version`: the adapter code version that produced the parsed record.

## Conflict Classification (Never Averaged)

`scripts/reconcile_sources.py:reconcile_metric` classifies a canonical vs.
candidate value pair into exactly one of:

| Classification | Meaning | Handling |
| --- | --- | --- |
| `match` | Values are identical after normalization | Use canonical |
| `rounding` | Values differ within the caller's tolerance | Use canonical; note the tolerance-band difference |
| `period_mismatch` | Period type or period key differ | Not comparable; do not average |
| `consolidation_mismatch` | Consolidated vs. individual scope differ | Not comparable; do not average |
| `restatement` | One source reflects a later filing/restatement than the other | Prefer the newer filing id; do not average |
| `true_conflict` | Same period/unit/consolidation/restatement status, values still differ beyond tolerance | Block; requires a `FIN-DATA-CONFLICT-*` open question before the thesis refreshes |

Values are compared **only** after unit, currency, period type, consolidation
scope, and restatement status all match. A conflict is never resolved by
averaging the two numbers.

## Reconciliation And Question Lifecycle

- A `true_conflict` on a **required** metric (revenue, net income, assets,
  equity, CFO, diluted shares, current P/E, current P/B) opens a
  `FIN-DATA-CONFLICT-<slug>` question in the `FIN-DATA` namespace and blocks
  `investment-thesis` from refreshing until it is resolved (financial-analysis's
  gate should treat this the same as a `blocked` required input).
- A conflict on an **optional** cross-check metric degrades the affected
  fetch's status instead of blocking downstream stages.

## Source Repositioning (Task 8 Step 4)

- **TWSE/TPEx official values**: canonical when the contract's period/unit/
  consolidation/restatement fields match. (TPEx is currently unreachable —
  see the verified findings above; its tier assignment stands, but in
  practice it fails closed until the certificate is fixed.)
- **FinMind**: normalized history/cache, marked `secondary_aggregator` until
  reconciled against an official value for the same period.
- **Goodinfo**: temporary annual fallback / sanity check, not the primary
  financial-analysis source once official coverage exists for a metric.
- **Yahoo**: local profile/discovery fallback; excluded from `shareable`
  research-summary render payloads (`scripts/build_research_summary.py`
  never reads `yahoo-data.json` into the payload's `sources` list).

## Do Not

- Do not disable TLS certificate verification (`verify=False`) in any
  production fetch path. A TLS failure is a source failure.
- Do not construct an unsafely-shelled `curl` command as a verification
  bypass.
- Do not average conflicting values across sources under any classification.
- Do not claim "official three statements" until MOPS/XBRL coverage is
  proven (see `docs/adr/0001-mops-xbrl-ingestion.md`, Task 10).
