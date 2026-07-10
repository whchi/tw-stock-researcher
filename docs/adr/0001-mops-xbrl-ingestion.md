# ADR 0001: MOPS XBRL Ingestion Boundary

- Status: Decided
- Date: 2026-07-11
- Decision: **`manual_only`**

## Context

`docs/source-policy.md` ranks MOPS/XBRL as the highest-priority source for
complete financial statements, notes, audit opinions, and restatements, but
gates production automation on this ADR (Task 10 of
`docs/superpowers/plans/2026-07-10-workflow-contract-hardening.md`). This
task selects exactly one of three outcomes —
`approved_for_follow_up_implementation`, `manual_only`, or
`paid_feed_required` — based on verified terms-of-use and access-path
findings, not assumption. No production XBRL fetcher exists anywhere in
`scripts/`; this ADR does not add one.

## Step 1: Terms And Access Path (Verified 2026-07-11)

Findings below were obtained by directly fetching the cited official pages
and reading their live content (via `mcp__plugin_context-mode_context-mode__ctx_fetch_and_index`),
not by inference from training data.

### Automated retrieval is prohibited without TWSE's consent

[TWSE Terms of Use](https://www.twse.com.tw/zh/terms/use.html), clause 6
(「下載軟體或資料」), verbatim:

> 非依臺灣證券交易所同意之方式或經臺灣證券交易所同意者，禁止透過包括但不限於自動化裝置、指令碼、自動程式、蜘蛛程式、爬蟲程式或擷取程式等方式下載本網站之軟體或資料。

Translation: automated devices, scripts, bots, spiders, crawlers, or
scraping programs are prohibited from downloading site software or data
unless TWSE has consented. Clause 8 carves out exactly one blanket
exception: data TWSE has separately authorized for redistribution through
「政府資料開放平臺」(the government open-data platform) — i.e. the same
official OpenAPI endpoints this project already uses for TWSE/TDCC data
per `docs/source-policy.md`. MOPS (`mops.twse.com.tw`) is operated by TWSE
under this same terms umbrella; no separate, more permissive MOPS terms
page was found. XBRL filings and per-company financial statement pages are
not published through the OpenAPI/open-data exception — they are served
only through the MOPS web UI or the paid distribution channel below.

### The only sanctioned automated/bulk path is a paid subscription

[TWSE Data E-Shop — MOPS service list](https://eshop.twse.com.tw/zh/mops/list)
lists a dedicated push-delivery package for XBRL files:

> 套裝五 XBRL — 接收「XBRL」相關檔案資料 — NT$40,000 / 月

This is an explicit, priced, contractual channel for automated/bulk XBRL
file delivery. It is the only channel TWSE documents as consistent with
clause 6's "or TWSE has consented" exception for this dataset.

### No free bulk/API path for XBRL instance documents

[TWSE XBRL — 分類標準 (taxonomy standards)](https://www.twse.com.tw/XBRL/standard)
only links to taxonomy *schema* downloads (`mops.twse.com.tw/mops/web/t147sb01`,
「XBRL資訊平台 > XBRL案例文件下載 > 分類標準下載」) — the classification
scheme, not per-company instance documents. [TWSE XBRL — 關於XBRL](https://www.twse.com.tw/rwd/XBRL/about)
confirms Taiwan's capital market has required XBRL filing since Q2 2010
(民國99年第2季) and Inline XBRL (iXBRL) since Q1 2019 (民國108年第1季), with
three report scopes — individual (個別), entity (個體), and consolidated
(合併) — each assembled from modular taxonomies. None of this changes the
access-path conclusion: individual instance documents are retrieved
per-filing through the MOPS web UI (human-driven) or through the paid
套裝五 feed (automated, contractual).

### Conclusion for Step 1

Automated retrieval of MOPS XBRL filings without TWSE's consent is
explicitly prohibited by TWSE's own terms. The only TWSE-sanctioned
automated channel is a paid subscription (NT$40,000/month for the XBRL
package alone). `docs/source-policy.md`'s own source table already notes
the Data E-Shop is "not economical for one-stock-at-a-time local
research" — this project's actual and only use case. Permission for free
automated production ingestion is not unclear; it is denied by default and
only available at a cost disproportionate to this project's scope.

## Step 2: Technical Feasibility Spike — Not Performed On Real Filings

The plan's Step 2 calls for a local parser feasibility spike across one
general, one financial, and one mixed-industry issuer over eight quarters
using "legally downloaded samples." This ADR does **not** attempt that
spike against real per-filing XBRL instance documents, because every
practical way to obtain those samples in this session (WebFetch, scripted
`ctx_fetch_and_index`, or any other tool-driven request against
`mops.twse.com.tw`) is itself the kind of automated retrieval clause 6
prohibits — the plan's own guardrail says not to route around this gate
"with hidden form posts, cookies, CAPTCHA automation, or browser
scraping," and a tool-driven fetch of gated per-filing MOPS pages is not
meaningfully different from that.

What is documented instead, from TWSE's own public XBRL program pages
(not scraped filing data):

- Three report scopes exist per filing: individual / entity / consolidated
  — a future parser must treat these as distinct facts, never merged.
- iXBRL has been the filing format since Q1 2019; pre-2019 filings use
  plain XBRL — a future parser needs two code paths or a normalizing
  pre-processor.
- Taxonomies are versioned and industry-specific (general, financial,
  insurance, securities, etc.), matching this project's existing
  `docs/source-policy.md` note that TWSE's own official adapters already
  have to special-case industry-specific schemas for non-XBRL datasets.

If a future decision reopens this ADR (e.g. the project acquires the
paid feed), the technical spike should be re-run first, using instance
documents obtained through that paid channel or through a human manually
saving individual filings from the MOPS UI — not through this project's
automated tooling.

## Step 3: Decision

**Outcome: `manual_only`.**

- Automated, unattended MOPS XBRL ingestion is not implemented and must
  not be implemented under the current terms, because:
  1. TWSE's terms of use prohibit automated retrieval without consent
     (Step 1).
  2. The one sanctioned automated channel (`套裝五 XBRL`, NT$40,000/month)
     is a paid contractual feed this project has no budget or mandate to
     acquire — this is a `paid_feed_required` fact, not a `manual_only`
     ambiguity, but the project's stated one-stock-at-a-time scope makes
     acquiring that feed impractical, so the operative outcome for
     day-to-day work is `manual_only`.
- MOPS remains available exactly as it already is used elsewhere in this
  repository: a human-driven cross-check. `financial-analysis.md` already
  requires a manually-included "MOPS official filing URL" per
  `AGENTS.md`'s Financial Analysis Conventions; that pattern is confirmed,
  not changed, by this ADR.
- Redistribution constraint: even under the paid feed, TWSE's terms
  (clause 8) require written consent before redistributing site content;
  any future paid-feed integration must also resolve redistribution terms
  before any XBRL-derived value appears in a `shareable` research-summary
  payload (`scripts/research_summary_contract.py`'s `distribution:
  shareable` rule already rejects `restricted`-tier sources for this
  reason).
- Operational risk if this decision is ignored: a hidden or ad-hoc scraper
  targeting `mops.twse.com.tw`'s XBRL pages would violate TWSE's terms of
  use (contract/ToS risk, not a technical risk), independent of whether
  the scraper works.
- Re-evaluation trigger: if the project's scope changes to justify the
  paid feed, or TWSE publishes a free official OpenAPI/open-data path for
  XBRL instance documents (as it already has for price, revenue, and
  company-master data), reopen this ADR as a new numbered ADR rather than
  editing this one.

## Consequences

- No `scripts/fetch_mops_xbrl.py` or equivalent exists or should be added
  while this decision stands.
- `docs/source-policy.md` keeps MOPS as a manually-cited cross-check link,
  not a fetched dataset, consistent with the current fetchers
  (`fetch_goodinfo.py`, `fetch_fundamentals.py`, `fetch_finmind.py`,
  `fetch_official_issuer.py`) none of which touch `mops.twse.com.tw`.
- `tests/fixtures/mops-xbrl/README.md` documents how a human would supply
  legally-obtained sample filings if this ADR is ever reopened; no sample
  XBRL files are checked into this repository.

## References

- [TWSE Terms of Use](https://www.twse.com.tw/zh/terms/use.html)
- [TWSE XBRL — 關於XBRL](https://www.twse.com.tw/rwd/XBRL/about)
- [TWSE XBRL — 分類標準](https://www.twse.com.tw/XBRL/standard)
- [TWSE Data E-Shop — MOPS service list](https://eshop.twse.com.tw/zh/mops/list)
- `docs/source-policy.md`
- `docs/superpowers/plans/2026-07-10-workflow-contract-hardening.md`, Task 10
